# Copyright 2025 JABAS AI. Proprietary.
"""Autonomy health aggregator node (C9).

Collects per-subsystem health signals, computes a single AutonomyHealth state,
and derives a recommended speed cap via a monotone health->speed policy so the
behavior layer can degrade gracefully instead of failing hard.

This is a skeleton: subsystem inputs are simple Float32 topics. In production,
replace with typed health messages / diagnostics and calibrated OOD scores.
"""
from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32

from jabas_interfaces.msg import AutonomyHealth


class HealthAggregator(Node):
    """Aggregates subsystem confidences into one AutonomyHealth state."""

    def __init__(self) -> None:
        super().__init__("health_aggregator")

        # Thresholds (declare as parameters so they are tunable at runtime).
        self.declare_parameter("degraded_threshold", 0.6)
        self.declare_parameter("critical_threshold", 0.3)
        self.declare_parameter("max_speed", 1.5)  # m/s at full health
        self.declare_parameter("min_speed", 0.0)  # m/s at critical health
        self.declare_parameter("publish_rate_hz", 5.0)

        # Latest subsystem confidences in [0, 1]; start optimistic-but-unknown.
        self._localization = 1.0
        self._perception = 1.0
        self._planner = 1.0
        self._comms_rtt_ms = -1.0

        self.create_subscription(
            Float32, "health/localization_confidence", self._on_localization, 10
        )
        self.create_subscription(
            Float32, "health/perception_confidence", self._on_perception, 10
        )
        self.create_subscription(
            Float32, "health/planner_feasibility", self._on_planner, 10
        )
        self.create_subscription(Float32, "health/comms_rtt_ms", self._on_comms, 10)

        self._pub = self.create_publisher(AutonomyHealth, "autonomy_health", 10)

        rate = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / max(0.1, rate), self._tick)
        self.get_logger().info("health_aggregator up")

    # --- subscription callbacks ---
    def _on_localization(self, msg: Float32) -> None:
        self._localization = float(msg.data)

    def _on_perception(self, msg: Float32) -> None:
        self._perception = float(msg.data)

    def _on_planner(self, msg: Float32) -> None:
        self._planner = float(msg.data)

    def _on_comms(self, msg: Float32) -> None:
        self._comms_rtt_ms = float(msg.data)

    # --- policy ---
    def _tick(self) -> None:
        degraded = float(self.get_parameter("degraded_threshold").value)
        critical = float(self.get_parameter("critical_threshold").value)
        v_max = float(self.get_parameter("max_speed").value)
        v_min = float(self.get_parameter("min_speed").value)

        # Overall confidence is the weakest link (min), a conservative choice.
        overall = min(self._localization, self._perception, self._planner)

        warnings: list[str] = []
        if self._localization < degraded:
            warnings.append("LOW_LOCALIZATION_CONFIDENCE")
        if self._perception < degraded:
            warnings.append("LOW_PERCEPTION_CONFIDENCE")
        if self._planner < degraded:
            warnings.append("PLANNER_STRUGGLING")

        msg = AutonomyHealth()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.localization_confidence = self._localization
        msg.perception_confidence = self._perception
        msg.planner_feasibility = self._planner
        msg.comms_rtt_ms = self._comms_rtt_ms
        msg.active_warnings = warnings

        if overall < critical:
            msg.level = AutonomyHealth.LEVEL_CRITICAL
        elif overall < degraded:
            msg.level = AutonomyHealth.LEVEL_DEGRADED
        else:
            msg.level = AutonomyHealth.LEVEL_OK

        # Monotone health->speed mapping: linear ramp between critical and 1.0.
        span = max(1e-3, 1.0 - critical)
        scale = max(0.0, min(1.0, (overall - critical) / span))
        msg.recommended_max_speed = v_min + scale * (v_max - v_min)

        self._pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = HealthAggregator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
