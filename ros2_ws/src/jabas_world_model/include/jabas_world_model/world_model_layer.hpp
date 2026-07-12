// Copyright 2025 JABAS AI. Proprietary.
#ifndef JABAS_WORLD_MODEL__WORLD_MODEL_LAYER_HPP_
#define JABAS_WORLD_MODEL__WORLD_MODEL_LAYER_HPP_

#include <memory>
#include <string>
#include <mutex>

#include "rclcpp/rclcpp.hpp"
#include "nav2_costmap_2d/layer.hpp"
#include "nav2_costmap_2d/layered_costmap.hpp"
#include "nav_msgs/msg/occupancy_grid.hpp"

namespace jabas_world_model
{

/// Nav2 costmap layer that renders the world model's traversability grid into
/// the costmap. This is the migration bridge (see 10-implementation-guide.md
/// section 2): existing NavFn + MPPI keep running unchanged while the world
/// model becomes the source of truth. Combines with existing costs via max.
class WorldModelLayer : public nav2_costmap_2d::Layer
{
public:
  WorldModelLayer() = default;

  void onInitialize() override;
  void updateBounds(
    double robot_x, double robot_y, double robot_yaw,
    double * min_x, double * min_y, double * max_x, double * max_y) override;
  void updateCosts(
    nav2_costmap_2d::Costmap2D & master_grid,
    int min_i, int min_j, int max_i, int max_j) override;
  void reset() override;
  bool isClearable() override {return false;}
  void onFootprintChanged() override {}

private:
  void gridCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg);

  rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr grid_sub_;
  nav_msgs::msg::OccupancyGrid::SharedPtr latest_grid_;
  std::mutex grid_mutex_;

  std::string topic_;
  double risk_lethal_threshold_{0.9};  // risk >= this -> LETHAL
  bool enabled_layer_{true};
  rclcpp::Logger logger_{rclcpp::get_logger("WorldModelLayer")};
};

}  // namespace jabas_world_model

#endif  // JABAS_WORLD_MODEL__WORLD_MODEL_LAYER_HPP_
