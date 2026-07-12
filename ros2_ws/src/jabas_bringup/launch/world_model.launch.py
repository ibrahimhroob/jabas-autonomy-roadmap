# Copyright 2025 JABAS AI. Proprietary.
"""Bring up the world model + health stack (Phase 0/1 skeleton).

Launches:
  - jabas_world_model/world_model_node   (persistent temporal world model, C1)
  - jabas_health/health_aggregator       (C9)
  - jabas_health/event_trigger           (data engine)

Use `use_sim_time:=true` when running against sim or a replayed bag so all
nodes share the /clock (required for deterministic replay -- see P0.1).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory("jabas_bringup")
    default_params = os.path.join(pkg_share, "config", "world_model.yaml")

    use_sim_time = LaunchConfiguration("use_sim_time")
    params_file = LaunchConfiguration("params_file")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use /clock (true for sim/replay).",
            ),
            DeclareLaunchArgument(
                "params_file",
                default_value=default_params,
                description="Path to the world model params YAML.",
            ),
            Node(
                package="jabas_world_model",
                executable="world_model_node",
                name="world_model_node",
                output="screen",
                parameters=[params_file, {"use_sim_time": use_sim_time}],
            ),
            Node(
                package="jabas_health",
                executable="health_aggregator",
                name="health_aggregator",
                output="screen",
                parameters=[{"use_sim_time": use_sim_time}],
            ),
            Node(
                package="jabas_health",
                executable="event_trigger",
                name="event_trigger",
                output="screen",
                parameters=[{"use_sim_time": use_sim_time}],
            ),
        ]
    )
