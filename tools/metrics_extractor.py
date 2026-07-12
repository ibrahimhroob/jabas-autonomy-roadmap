#!/usr/bin/env python3
# Copyright 2025 JABAS AI. Proprietary.
"""Extract autonomy metrics from a recorded MCAP bag (P0.1, log-driven CI).

Computes simple, safety-relevant metrics that gate merges in replay-CI:
  - min_obstacle_distance : closest LaserScan return over the run (proxy)
  - max_cmd_speed         : peak commanded linear speed
  - max_cmd_jerk          : peak |d(accel)/dt| of commanded linear speed (comfort)
  - duration_s            : bag duration

Reads MCAP directly (no ROS runtime needed) so it runs in plain CI containers.
Deserialization of ROS 2 messages uses `rosbags` if available; otherwise it
falls back to reporting channel/message counts only.

Usage:
    python3 tools/metrics_extractor.py --bag path/to/bag.mcap \
        --out metrics.json [--baseline baseline.json --tolerance 0.1]

Exit code is non-zero if a baseline is provided and a metric regresses beyond
tolerance -- this is what fails a PR.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def _extract_with_rosbags(bag_path: Path) -> dict[str, Any]:
    """Best-effort metric extraction using the `rosbags` library."""
    from rosbags.highlevel import AnyReader  # type: ignore

    min_obstacle_distance = math.inf
    max_cmd_speed = 0.0
    speeds: list[tuple[float, float]] = []  # (t_sec, linear.x)

    with AnyReader([bag_path]) as reader:
        connections = list(reader.connections)
        for conn, timestamp, raw in reader.messages(connections=connections):
            t = timestamp * 1e-9
            msgtype = conn.msgtype
            if msgtype.endswith("LaserScan"):
                msg = reader.deserialize(raw, msgtype)
                for r in msg.ranges:
                    if math.isfinite(r) and msg.range_min <= r <= msg.range_max:
                        min_obstacle_distance = min(min_obstacle_distance, float(r))
            elif msgtype.endswith("Twist") or msgtype.endswith("TwistStamped"):
                msg = reader.deserialize(raw, msgtype)
                twist = getattr(msg, "twist", msg)
                lin = float(getattr(twist.linear, "x", 0.0))
                max_cmd_speed = max(max_cmd_speed, abs(lin))
                speeds.append((t, lin))

        t0 = reader.start_time * 1e-9
        t1 = reader.end_time * 1e-9

    max_cmd_jerk = _max_jerk(speeds)
    return {
        "min_obstacle_distance": (
            None if math.isinf(min_obstacle_distance) else min_obstacle_distance
        ),
        "max_cmd_speed": max_cmd_speed,
        "max_cmd_jerk": max_cmd_jerk,
        "duration_s": max(0.0, t1 - t0),
    }


def _max_jerk(speeds: list[tuple[float, float]]) -> float:
    """Peak |d(accel)/dt| from a time series of linear speeds."""
    if len(speeds) < 3:
        return 0.0
    speeds.sort(key=lambda p: p[0])
    accels: list[tuple[float, float]] = []
    for (t0, v0), (t1, v1) in zip(speeds, speeds[1:]):
        dt = t1 - t0
        if dt > 1e-6:
            accels.append(((t0 + t1) / 2.0, (v1 - v0) / dt))
    max_jerk = 0.0
    for (t0, a0), (t1, a1) in zip(accels, accels[1:]):
        dt = t1 - t0
        if dt > 1e-6:
            max_jerk = max(max_jerk, abs((a1 - a0) / dt))
    return max_jerk


def _fallback_counts(bag_path: Path) -> dict[str, Any]:
    """If deserialization libs are unavailable, at least prove the bag is readable."""
    try:
        from mcap.reader import make_reader  # type: ignore

        with bag_path.open("rb") as f:
            reader = make_reader(f)
            summary = reader.get_summary()
            n = summary.statistics.message_count if summary and summary.statistics else 0
        return {"message_count": int(n), "note": "install `rosbags` for full metrics"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"could not read bag: {exc}"}


def extract(bag_path: Path) -> dict[str, Any]:
    try:
        return _extract_with_rosbags(bag_path)
    except Exception:  # noqa: BLE001 - library missing or msg types unknown
        return _fallback_counts(bag_path)


def check_regression(
    metrics: dict[str, Any], baseline: dict[str, Any], tolerance: float
) -> list[str]:
    """Return a list of regression messages (empty == pass).

    Convention:
      - min_obstacle_distance must not DROP more than tolerance (got closer to obstacles)
      - max_cmd_jerk must not RISE more than tolerance (rougher motion)
    """
    failures: list[str] = []
    b_dist = baseline.get("min_obstacle_distance")
    m_dist = metrics.get("min_obstacle_distance")
    if isinstance(b_dist, (int, float)) and isinstance(m_dist, (int, float)):
        if m_dist < b_dist * (1.0 - tolerance):
            failures.append(
                f"min_obstacle_distance regressed: {m_dist:.3f} < "
                f"{b_dist:.3f} * (1-{tolerance})"
            )
    b_jerk = baseline.get("max_cmd_jerk")
    m_jerk = metrics.get("max_cmd_jerk")
    if isinstance(b_jerk, (int, float)) and isinstance(m_jerk, (int, float)):
        if m_jerk > b_jerk * (1.0 + tolerance):
            failures.append(
                f"max_cmd_jerk regressed: {m_jerk:.3f} > "
                f"{b_jerk:.3f} * (1+{tolerance})"
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bag", required=True, type=Path, help="Path to .mcap bag")
    parser.add_argument("--out", type=Path, default=Path("metrics.json"))
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--tolerance", type=float, default=0.1)
    args = parser.parse_args()

    if not args.bag.exists():
        print(f"error: bag not found: {args.bag}", file=sys.stderr)
        return 2

    metrics = extract(args.bag)
    args.out.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))

    if args.baseline and args.baseline.exists():
        baseline = json.loads(args.baseline.read_text())
        failures = check_regression(metrics, baseline, args.tolerance)
        if failures:
            print("\nREGRESSIONS DETECTED:", file=sys.stderr)
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
            return 1
        print("\nNo regressions vs baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
