# JABAS Autonomy — ROS 2 Workspace Skeleton

Starter code for Phase 0/1 of the roadmap (see `../10-implementation-guide.md`). This is a **scaffold** to build on, not a finished stack. It compiles against **ROS 2 Jazzy + Nav2**; it was authored without an on-hand ROS 2 toolchain, so expect to run `colcon build` in your environment and fix minor distro-specific details (noted inline as `TODO`).

## What's here

| Package | Language | What it does | Roadmap ref |
|---|---|---|---|
| `jabas_interfaces` | msg/srv | The **contract**: `WorldModelSnapshot`, `GridLayer`, `TrackedObject`, `AutonomyHealth`, `QueryTraversability`. Everything else evolves behind this. | C1 / doc 10 §2 |
| `jabas_world_model` | C++ | Persistent, temporally-**decaying** world-model node (LaserScan + tf → log-odds grid → `OccupancyGrid` + `WorldModelSnapshot` + query service) **and** a Nav2 costmap **layer plugin** that bridges it into your existing NavFn/MPPI stack. | C1 / P1.1 |
| `jabas_health` | Python | Health **aggregator** (→ `AutonomyHealth` + graceful-degradation speed cap) and a data-engine **event trigger**. | C9 / P0.4 |
| `jabas_bringup` | launch/yaml | Launch + params, plus a `nav2_costmap_patch.yaml` showing how to add the world-model layer to your costmap. | — |
| `../tools/` | Python | `replay_runner.py` (deterministic replay) + `metrics_extractor.py` (log-driven CI metrics). | P0.1 |
| `../.github/workflows/` | CI | `ros2-build.yml` (build+lint) and `replay-ci.yml` (regression gate). | P0.1 |

## The one idea this scaffold demonstrates
The world-model node keeps a memory of observations and **decays** it over time. Setting `decay` closer to `1.0` makes the robot *remember* obstacles it can no longer see (fixing Nav2's oscillation / re-collision bug); lowering it makes the robot *forget* faster. The Nav2 layer plugin lets you adopt this **without changing your planner** — it just contributes cost to the existing costmap.

## Build
```bash
# ROS 2 Jazzy + Nav2 installed. From repo root:
cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Run (with a sim or a bag providing `scan` + `/tf` + `/clock`)
```bash
ros2 launch jabas_bringup world_model.launch.py use_sim_time:=true
# visualize /world_model_node/traversability (OccupancyGrid) in RViz/Foxglove
```

Wire into Nav2 by merging `src/jabas_bringup/config/nav2_costmap_patch.yaml` into your `nav2_params.yaml` (add `jabas_world_model_layer` to the `local_costmap` plugins list).

## Replay + metrics (outside the ROS build)
```bash
pip install -r ../tools/requirements.txt
python3 ../tools/metrics_extractor.py --bag some_run.mcap --out metrics.json
```

## Deliberate simplifications (your next PRs)
- Node uses `LaserScan` + a fixed global grid; production uses point clouds, a rolling window, and real semantics/elevation layers.
- No free-space ray-clearing yet (decay stands in). Add a proper inverse sensor model.
- `localization_confidence` is hard-coded 1.0 — wire the real integrity monitor (C7).
- Costmap layer assumes source grid and costmap share the global frame; add TF handling for mismatches.
- Do **not** commit large bags to git; use DVC/LFS or an artifact store for `tests/replay/`.
