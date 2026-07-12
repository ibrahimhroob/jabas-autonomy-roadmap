# Copyright 2025 JABAS AI. Proprietary.
"""Interesting-event trigger node (Phase 0, data engine).

Watches the AutonomyHealth stream and fires a trigger when the robot enters a
DEGRADED/CRITICAL state or a named warning appears. In production, a trigger
should snapshot a +/- N second MCAP clip and mark it for prioritized upload;
here we emit a std_msgs/String event marker and log it, leaving the clip
extraction to tools/replay_runner + a recorder (see 10-implementation-guide.md
section 3, P0.4).
"""
from __future__ import annotations

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from jabas_interfaces.msg import AutonomyHealth


class EventTrigger(Node):
    """Emits event markers on autonomy-health degradation (edge-triggered)."""

    def __init__(self) -> None:
        super().__init__("event_trigger")
        self.declare_parameter("cooldown_seconds", 10.0)
        self._last_level = AutonomyHealth.LEVEL_OK
        self._last_trigger_time = self.get_clock().now()

        self.create_subscription(
            AutonomyHealth, "autonomy_health", self._on_health, 10
        )
        self._pub = self.create_publisher(String, "data_engine/events", 10)
        self.get_logger().info("event_trigger up")

    def _on_health(self, msg: AutonomyHealth) -> None:
        # Edge-trigger on a worsening transition only.
        worsened = msg.level > self._last_level
        self._last_level = msg.level
        if not worsened or msg.level == AutonomyHealth.LEVEL_OK:
            return

        cooldown = float(self.get_parameter("cooldown_seconds").value)
        now = self.get_clock().now()
        elapsed = (now - self._last_trigger_time).nanoseconds * 1e-9
        if elapsed < cooldown:
            return
        self._last_trigger_time = now

        event = {
            "type": "health_degradation",
            "level": int(msg.level),
            "warnings": list(msg.active_warnings),
            "stamp_sec": msg.header.stamp.sec,
        }
        out = String()
        out.data = json.dumps(event)
        self._pub.publish(out)
        self.get_logger().warn(f"EVENT TRIGGERED: {out.data}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EventTrigger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
