// Copyright 2025 JABAS AI. Proprietary.
#include "jabas_world_model/world_model_node.hpp"

#include <algorithm>
#include <cmath>
#include <chrono>

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "tf2/LinearMath/Transform.h"
#include "tf2/LinearMath/Vector3.h"
#include "tf2/LinearMath/Quaternion.h"

using namespace std::chrono_literals;

namespace jabas_world_model
{

WorldModelNode::WorldModelNode(const rclcpp::NodeOptions & options)
: rclcpp::Node("world_model_node", options)
{
  // --- declare + read parameters ---
  global_frame_ = declare_parameter<std::string>("global_frame", "map");
  resolution_ = declare_parameter<double>("resolution", 0.1);
  width_m_ = declare_parameter<double>("width_m", 50.0);
  height_m_ = declare_parameter<double>("height_m", 50.0);
  decay_ = declare_parameter<double>("decay", 0.98);
  l_occ_ = declare_parameter<double>("log_odds_hit", 0.85);
  l_clamp_ = declare_parameter<double>("log_odds_clamp", 5.0);
  const double publish_rate = declare_parameter<double>("publish_rate_hz", 5.0);
  const std::string scan_topic = declare_parameter<std::string>("scan_topic", "scan");

  origin_x_ = -width_m_ / 2.0;
  origin_y_ = -height_m_ / 2.0;
  width_cells_ = static_cast<uint32_t>(std::round(width_m_ / resolution_));
  height_cells_ = static_cast<uint32_t>(std::round(height_m_ / resolution_));
  log_odds_.assign(static_cast<size_t>(width_cells_) * height_cells_, 0.0f);

  // --- tf ---
  tf_buffer_ = std::make_unique<tf2_ros::Buffer>(get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

  // --- interfaces ---
  scan_sub_ = create_subscription<sensor_msgs::msg::LaserScan>(
    scan_topic, rclcpp::SensorDataQoS(),
    std::bind(&WorldModelNode::scanCallback, this, std::placeholders::_1));

  grid_pub_ = create_publisher<nav_msgs::msg::OccupancyGrid>(
    "~/traversability", rclcpp::QoS(1).transient_local());
  snapshot_pub_ = create_publisher<jabas_interfaces::msg::WorldModelSnapshot>(
    "~/snapshot", rclcpp::QoS(1));

  query_srv_ = create_service<jabas_interfaces::srv::QueryTraversability>(
    "~/query_traversability",
    std::bind(&WorldModelNode::handleQuery, this,
      std::placeholders::_1, std::placeholders::_2));

  const auto period = std::chrono::duration<double>(1.0 / std::max(0.1, publish_rate));
  publish_timer_ = create_wall_timer(
    std::chrono::duration_cast<std::chrono::nanoseconds>(period),
    std::bind(&WorldModelNode::publishTimerCallback, this));

  RCLCPP_INFO(
    get_logger(),
    "world_model_node up: %ux%u cells @ %.2fm, frame=%s, decay=%.3f",
    width_cells_, height_cells_, resolution_, global_frame_.c_str(), decay_);
}

float WorldModelNode::logOddsToProb(float l)
{
  return 1.0f - 1.0f / (1.0f + std::exp(l));
}

bool WorldModelNode::worldToIndex(double x, double y, size_t & index) const
{
  const int col = static_cast<int>(std::floor((x - origin_x_) / resolution_));
  const int row = static_cast<int>(std::floor((y - origin_y_) / resolution_));
  if (col < 0 || row < 0 ||
    col >= static_cast<int>(width_cells_) || row >= static_cast<int>(height_cells_))
  {
    return false;
  }
  index = static_cast<size_t>(row) * width_cells_ + static_cast<size_t>(col);
  return true;
}

void WorldModelNode::scanCallback(const sensor_msgs::msg::LaserScan::SharedPtr scan)
{
  // Look up the transform from the scan frame to the global frame at scan time.
  geometry_msgs::msg::TransformStamped tf_msg;
  try {
    tf_msg = tf_buffer_->lookupTransform(
      global_frame_, scan->header.frame_id, scan->header.stamp,
      rclcpp::Duration::from_seconds(0.1));
  } catch (const tf2::TransformException & ex) {
    RCLCPP_WARN_THROTTLE(
      get_logger(), *get_clock(), 2000, "TF unavailable: %s", ex.what());
    return;
  }

  tf2::Transform t;
  t.setOrigin(tf2::Vector3(
      tf_msg.transform.translation.x,
      tf_msg.transform.translation.y,
      tf_msg.transform.translation.z));
  t.setRotation(tf2::Quaternion(
      tf_msg.transform.rotation.x, tf_msg.transform.rotation.y,
      tf_msg.transform.rotation.z, tf_msg.transform.rotation.w));

  const float l_clamp = static_cast<float>(l_clamp_);
  double angle = scan->angle_min;
  for (const float range : scan->ranges) {
    if (std::isfinite(range) && range >= scan->range_min && range <= scan->range_max) {
      // Endpoint in the scan frame, then transformed to the global frame.
      const tf2::Vector3 p_scan(range * std::cos(angle), range * std::sin(angle), 0.0);
      const tf2::Vector3 p_world = t * p_scan;
      size_t idx;
      if (worldToIndex(p_world.x(), p_world.y(), idx)) {
        // Inverse sensor model: raise occupancy at the hit cell.
        // TODO(perception): also ray-clear free space between sensor and hit.
        log_odds_[idx] = std::clamp(
          log_odds_[idx] + static_cast<float>(l_occ_), -l_clamp, l_clamp);
      }
    }
    angle += scan->angle_increment;
  }
}

void WorldModelNode::publishTimerCallback()
{
  // Temporal decay: unobserved cells slowly relax toward "unknown".
  const float decay = static_cast<float>(decay_);
  for (auto & l : log_odds_) {
    l *= decay;
  }
  ++version_;

  const auto now = this->now();

  // --- OccupancyGrid (for RViz + the Nav2 costmap layer bridge) ---
  nav_msgs::msg::OccupancyGrid grid;
  grid.header.stamp = now;
  grid.header.frame_id = global_frame_;
  grid.info.resolution = static_cast<float>(resolution_);
  grid.info.width = width_cells_;
  grid.info.height = height_cells_;
  grid.info.origin.position.x = origin_x_;
  grid.info.origin.position.y = origin_y_;
  grid.info.origin.orientation.w = 1.0;
  grid.data.resize(log_odds_.size());

  // --- WorldModelSnapshot (the platform contract) ---
  jabas_interfaces::msg::WorldModelSnapshot snap;
  snap.header.stamp = now;
  snap.header.frame_id = global_frame_;
  snap.version = version_;
  snap.localization_confidence = 1.0f;  // TODO(localization): wire real integrity (C7).

  auto & trav = snap.traversability;
  trav.header = snap.header;
  trav.resolution = static_cast<float>(resolution_);
  trav.width = width_cells_;
  trav.height = height_cells_;
  trav.origin = grid.info.origin;
  trav.values.resize(log_odds_.size());

  for (size_t i = 0; i < log_odds_.size(); ++i) {
    const float p = logOddsToProb(log_odds_[i]);   // occupancy prob == risk
    trav.values[i] = p;
    grid.data[i] = static_cast<int8_t>(std::lround(p * 100.0f));
  }

  grid_pub_->publish(grid);
  snapshot_pub_->publish(snap);
}

void WorldModelNode::handleQuery(
  const std::shared_ptr<jabas_interfaces::srv::QueryTraversability::Request> req,
  std::shared_ptr<jabas_interfaces::srv::QueryTraversability::Response> res)
{
  const size_t n = req->query_points.size();
  res->risk.resize(n);
  res->uncertainty.resize(n);
  res->in_bounds.resize(n);
  for (size_t k = 0; k < n; ++k) {
    size_t idx;
    if (worldToIndex(req->query_points[k].x, req->query_points[k].y, idx)) {
      res->risk[k] = logOddsToProb(log_odds_[idx]);
      // Uncertainty proxy: max near log-odds==0 (unknown), low when confident.
      res->uncertainty[k] = 1.0f - std::abs(std::tanh(log_odds_[idx]));
      res->in_bounds[k] = true;
    } else {
      res->risk[k] = 0.0f;
      res->uncertainty[k] = 1.0f;
      res->in_bounds[k] = false;
    }
  }
}

}  // namespace jabas_world_model

#include "rclcpp_components/register_node_macro.hpp"
// Registers the node as a composable component. The standalone executable
// `world_model_node` is generated by rclcpp_components_register_node in
// CMakeLists.txt, so no hand-written main() is needed here.
RCLCPP_COMPONENTS_REGISTER_NODE(jabas_world_model::WorldModelNode)
