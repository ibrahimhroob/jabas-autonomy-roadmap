// Copyright 2025 JABAS AI. Proprietary.
#ifndef JABAS_WORLD_MODEL__WORLD_MODEL_NODE_HPP_
#define JABAS_WORLD_MODEL__WORLD_MODEL_NODE_HPP_

#include <memory>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "nav_msgs/msg/occupancy_grid.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"

#include "jabas_interfaces/msg/world_model_snapshot.hpp"
#include "jabas_interfaces/srv/query_traversability.hpp"

namespace jabas_world_model
{

/// Minimal but real persistent, temporal world model (skeleton for C1).
///
/// It maintains a fixed, georeferenced log-odds occupancy grid in a global
/// frame. Laser hits raise a cell's occupancy; a per-cycle exponential decay
/// slowly forgets stale observations. This directly fixes Nav2's "memoryless
/// costmap" bug (persistence) while still forgetting genuinely-cleared space
/// (decay). Occupancy is exposed as a traversability risk in [0, 1].
///
/// This is intentionally simple. Production TODOs are marked inline.
class WorldModelNode : public rclcpp::Node
{
public:
  explicit WorldModelNode(const rclcpp::NodeOptions & options);

private:
  void scanCallback(const sensor_msgs::msg::LaserScan::SharedPtr scan);
  void publishTimerCallback();
  void handleQuery(
    const std::shared_ptr<jabas_interfaces::srv::QueryTraversability::Request> req,
    std::shared_ptr<jabas_interfaces::srv::QueryTraversability::Response> res);

  // Convert a world (x, y) to a flat grid index. Returns false if out of bounds.
  bool worldToIndex(double x, double y, size_t & index) const;
  // Occupancy probability [0, 1] from log-odds.
  static float logOddsToProb(float l);

  // --- parameters ---
  std::string global_frame_;
  double resolution_{0.1};      // meters/cell
  double width_m_{50.0};        // grid extent in x (meters)
  double height_m_{50.0};       // grid extent in y (meters)
  double origin_x_{-25.0};      // world coord of cell (0,0), lower-left
  double origin_y_{-25.0};
  double decay_{0.98};          // multiplicative log-odds decay per publish cycle
  double l_occ_{0.85};          // log-odds increment per hit (~inverse sensor model)
  double l_clamp_{5.0};         // clamp |log-odds|

  // --- state ---
  uint32_t width_cells_{0};
  uint32_t height_cells_{0};
  std::vector<float> log_odds_;
  uint64_t version_{0};

  // --- ROS ---
  rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;
  rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr grid_pub_;
  rclcpp::Publisher<jabas_interfaces::msg::WorldModelSnapshot>::SharedPtr snapshot_pub_;
  rclcpp::Service<jabas_interfaces::srv::QueryTraversability>::SharedPtr query_srv_;
  rclcpp::TimerBase::SharedPtr publish_timer_;

  std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};

}  // namespace jabas_world_model

#endif  // JABAS_WORLD_MODEL__WORLD_MODEL_NODE_HPP_
