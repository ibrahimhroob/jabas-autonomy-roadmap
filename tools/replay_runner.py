#!/usr/bin/env python3
# Copyright 2025 JABAS AI. Proprietary.
"""Deterministic replay runner (P0.1).

Re-runs the autonomy node graph against a recorded MCAP bag under simulated
time and records the outputs to a new bag. This is the foundation of debugging,
regression testing, and the data engine (see 10-implementation-guide.md sec 3).

It orchestrates ROS 2 CLI tools, so it must run in a sourced ROS 2 environment
(it does NOT import rclpy). Determinism checklist enforced here:
  - use_sim_time:=true so nodes consume the bag's /clock
  - `ros2 bag play --clock` publishes /clock from the bag
  - single-threaded executors + fixed seeds are the NODES' responsibility

Usage (inside a ROS 2 env):
    python3 tools/replay_runner.py \
        --input-bag bags/incident_042 \
        --launch jabas_bringup world_model.launch.py \
        --record-topics /world_model_node/traversability /cmd_vel /autonomy_health \
        --output-bag out/incident_042_replay
"""
from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def _require(cmd: str) -> None:
    if shutil.which(cmd) is None:
        print(
            f"error: '{cmd}' not found. Source your ROS 2 environment first "
            "(e.g. `source /opt/ros/jazzy/setup.bash`).",
            file=sys.stderr,
        )
        raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-bag", required=True, type=Path)
    parser.add_argument("--launch", nargs=2, metavar=("PKG", "FILE"), required=True)
    parser.add_argument("--record-topics", nargs="+", required=True)
    parser.add_argument("--output-bag", required=True, type=Path)
    parser.add_argument("--rate", type=float, default=1.0, help="playback rate")
    parser.add_argument("--settle-seconds", type=float, default=2.0)
    args = parser.parse_args()

    _require("ros2")
    if not args.input_bag.exists():
        print(f"error: input bag not found: {args.input_bag}", file=sys.stderr)
        return 2
    if args.output_bag.exists():
        shutil.rmtree(args.output_bag)

    pkg, launch_file = args.launch
    procs: list[subprocess.Popen] = []
    try:
        # 1) Bring up the node graph under sim time.
        procs.append(
            subprocess.Popen(
                ["ros2", "launch", pkg, launch_file, "use_sim_time:=true"]
            )
        )
        time.sleep(args.settle_seconds)  # let nodes initialize + discover

        # 2) Start recording the outputs of interest.
        procs.append(
            subprocess.Popen(
                ["ros2", "bag", "record", "-o", str(args.output_bag), *args.record_topics]
            )
        )
        time.sleep(1.0)

        # 3) Play the input bag, publishing /clock; block until it finishes.
        play = subprocess.run(
            [
                "ros2", "bag", "play", str(args.input_bag),
                "--clock", "--rate", str(args.rate),
            ],
            check=False,
        )
        time.sleep(args.settle_seconds)  # flush trailing messages
        print(f"replay finished (play rc={play.returncode}); output: {args.output_bag}")
        return play.returncode
    finally:
        # Tear down recorder + node graph cleanly.
        for p in reversed(procs):
            p.send_signal(signal.SIGINT)
        for p in reversed(procs):
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    raise SystemExit(main())
