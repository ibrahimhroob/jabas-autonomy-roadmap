// Copyright 2025 JABAS AI. Proprietary.
#include "jabas_world_model/world_model_layer.hpp"

#include <algorithm>
#include <cmath>

#include "nav2_costmap_2d/cost_values.hpp"

namespace jabas_world_model
{

void WorldModelLayer::onInitialize()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error{"Failed to lock node in WorldModelLayer"};
  }
  logger_ = node->get_logger();

  declareParameter("enabled", rclcpp::ParameterValue(true));
  declareParameter("topic", rclcpp::ParameterValue(std::string("/world_model_node/traversability")));
  declareParameter("risk_lethal_threshold", rclcpp::ParameterValue(0.9));

  node->get_parameter(name_ + ".enabled", enabled_layer_);
  node->get_parameter(name_ + ".topic", topic_);
  node->get_parameter(name_ + ".risk_lethal_threshold", risk_lethal_threshold_);

  grid_sub_ = node->create_subscription<nav_msgs::msg::OccupancyGrid>(
    topic_, rclcpp::QoS(1).transient_local(),
    std::bind(&WorldModelLayer::gridCallback, this, std::placeholders::_1));

  current_ = true;
  RCLCPP_INFO(logger_, "WorldModelLayer initialized, subscribing to '%s'", topic_.c_str());
}

void WorldModelLayer::gridCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg)
{
  std::lock_guard<std::mutex> lock(grid_mutex_);
  latest_grid_ = msg;
}

void WorldModelLayer::updateBounds(
  double /*robot_x*/, double /*robot_y*/, double /*robot_yaw*/,
  double * min_x, double * min_y, double * max_x, double * max_y)
{
  if (!enabled_layer_) {
    return;
  }
  std::lock_guard<std::mutex> lock(grid_mutex_);
  if (!latest_grid_) {
    return;
  }
  const auto & info = latest_grid_->info;
  const double gx0 = info.origin.position.x;
  const double gy0 = info.origin.position.y;
  const double gx1 = gx0 + info.width * info.resolution;
  const double gy1 = gy0 + info.height * info.resolution;

  *min_x = std::min(*min_x, gx0);
  *min_y = std::min(*min_y, gy0);
  *max_x = std::max(*max_x, gx1);
  *max_y = std::max(*max_y, gy1);
}

void WorldModelLayer::updateCosts(
  nav2_costmap_2d::Costmap2D & master_grid,
  int min_i, int min_j, int max_i, int max_j)
{
  if (!enabled_layer_) {
    return;
  }
  std::lock_guard<std::mutex> lock(grid_mutex_);
  if (!latest_grid_) {
    return;
  }
  const auto & info = latest_grid_->info;
  const auto & data = latest_grid_->data;

  for (int j = min_j; j < max_j; ++j) {
    for (int i = min_i; i < max_i; ++i) {
      // Master cell -> world coordinates.
      double wx, wy;
      master_grid.mapToWorld(i, j, wx, wy);

      // World -> source-grid cell.
      const int gi = static_cast<int>(std::floor((wx - info.origin.position.x) / info.resolution));
      const int gj = static_cast<int>(std::floor((wy - info.origin.position.y) / info.resolution));
      if (gi < 0 || gj < 0 ||
        gi >= static_cast<int>(info.width) || gj >= static_cast<int>(info.height))
      {
        continue;
      }
      const int8_t occ = data[static_cast<size_t>(gj) * info.width + gi];
      if (occ < 0) {
        continue;  // unknown -> leave underlying cost untouched
      }
      const double risk = static_cast<double>(occ) / 100.0;

      unsigned char cost;
      if (risk >= risk_lethal_threshold_) {
        cost = nav2_costmap_2d::LETHAL_OBSTACLE;
      } else {
        cost = static_cast<unsigned char>(
          std::lround(risk * (nav2_costmap_2d::INSCRIBED_INFLATED_OBSTACLE - 1)));
      }

      // Combine with existing cost via max (never lower another layer's cost).
      const unsigned char old_cost = master_grid.getCost(i, j);
      if (old_cost == nav2_costmap_2d::NO_INFORMATION || cost > old_cost) {
        master_grid.setCost(i, j, cost);
      }
    }
  }
}

void WorldModelLayer::reset()
{
  std::lock_guard<std::mutex> lock(grid_mutex_);
  latest_grid_.reset();
  current_ = false;
}

}  // namespace jabas_world_model

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(jabas_world_model::WorldModelLayer, nav2_costmap_2d::Layer)
