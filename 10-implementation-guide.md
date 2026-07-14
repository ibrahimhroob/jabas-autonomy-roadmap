# 10 — Implementation Guide (Build Plan, Verified Repos, Code Architecture)

This is the engineering companion to `05-flagship-projects.md`. Where `05` says *what* and *when*, this says *how*, *with which existing code*, and *what "done" looks like in the terminal*. Every external repo below was verified as real and current at the time of writing — but **always re-check the repo's README for your ROS 2 distro/branch**, because APIs and branches move.

> **Golden rule of this guide:** integrate before you invent. For each capability there is a battle-tested open-source project you should stand on. You write the *glue, the ag-specific logic, and the interfaces* — not another SLAM library.

---

## 0. Platform decisions (make these first, they're expensive to change)

| Decision | Recommendation | Alternatives | Why |
|---|---|---|---|
| **ROS 2 distro** | **Jazzy Jalisco** (LTS, Ubuntu 24.04) now; plan to track **Kilted** for `rmw_zenoh` Tier-1 | Humble (older LTS, very stable) | LTS = 5yr support; Jazzy is the current production sweet spot. Avoid non-LTS for a product. |
| **RMW (middleware)** | **Cyclone DDS** on-robot today; **`rmw_zenoh`** for robot↔cloud/multi-robot, moving to primary as it matures | Fast DDS (default) | Cyclone = predictable; Zenoh = built for lossy/WAN/mesh — ideal for rural fleets. [rmw_zenoh](https://github.com/ros2/rmw_zenoh) is Tier-1 as of ROS 2 Kilted. |
| **On-robot compute** | **NVIDIA Jetson Orin** (AGX/NX) | x86 + discrete GPU | Isaac ROS accelerated packages target Orin; power/size fit ag robots. |
| **Safety compute** | Separate **safety MCU/PLC** (rated) running the safety core | RT thread on main SoC (worse) | Independence = the whole point (see `01` Layer 9). |
| **Languages** | **C++20** hot path (perception/planning/control), **Python** for ML training, tooling, glue | Rust (great, smaller ecosystem) | Matches ROS 2 + the ecosystem below. |
| **Log format** | **MCAP** (ROS 2 default) | SQLite3 (legacy) | Append-only, fast, self-describing, tool-rich. [foxglove/mcap](https://github.com/foxglove/mcap). |
| **Visualization** | **Foxglove** + **rerun** + RViz2 | RViz2 only | Foxglove for logs/remote; rerun for ML/temporal debugging. |
| **Simulator** | **Gazebo (Harmonic/Ionic)** for physics/CI + **NVIDIA Isaac Sim** for photoreal sensor sim/synthetic data | Unity, CARLA | Gazebo = free, ROS-native, CI-friendly; Isaac = photoreal + domain randomization. |
| **CI** | **GitHub Actions** + `colcon` + containerized replay | GitLab CI, Jenkins | Wherever your code lives; the *replay-in-CI* part is what matters. |
| **Cloud** | **Kubernetes** + object storage (S3/MinIO) + a time-series DB; consider a managed robotics data platform for ingestion | Fully managed (Formant/Foxglove) vs fully DIY | Own the schema; buy the undifferentiated plumbing. |
| **Dataset/model versioning** | **DVC** (or lakeFS) + a model registry (MLflow) | Git-LFS (worse for big data) | Reproducible data + models = the data engine's backbone. |

---

## 1. Repository & workspace structure (monorepo)

A single monorepo keeps interfaces, code, sim, and infra in lockstep. Suggested layout:

```
jabas-autonomy/
├── ros2_ws/src/
│   ├── jabas_interfaces/        # ★ ALL msg/srv/action contracts (the stable API)
│   │   ├── msg/                 #   WorldModelSnapshot.msg, Traversability.msg, ...
│   │   └── srv/                 #   QueryTraversability.srv, ...
│   ├── jabas_world_model/       # C1 — persistent semantic temporal world model
│   ├── jabas_perception/        # C2/C3 perception + traversability nodes
│   ├── jabas_localization/      # C7 fusion + integrity monitor
│   ├── jabas_prediction/        # C4 prediction
│   ├── jabas_planning/          # C5/C6 planner extensions, Nav2 plugins/critics
│   ├── jabas_behavior/          # behavior trees + health-reactive logic
│   ├── jabas_safety/            # safety-core interface + monitors (mirror of MCU logic)
│   ├── jabas_health/            # C9 health aggregation + navigation health monitor
│   ├── jabas_fleet/             # C10 fleet client
│   ├── jabas_bringup/           # launch files, params, composition
│   └── jabas_sim/               # Gazebo/Isaac assets, world+robot models
├── ml/                          # training pipelines (Python), separate from ros2_ws
│   ├── traversability/          # C3 models
│   ├── prediction/              # C4 models
│   └── datasets/                # DVC-tracked dataset definitions
├── cloud/                       # K8s manifests, ingestion, map/experience services
├── tools/                       # replay runner, log triage, event triggers
├── sim_scenarios/               # golden + failure scenarios for CI
└── .github/workflows/           # replay-CI, build, lint
```

Key principle: **`jabas_interfaces` is sacred.** It's the world-model contract from `01`. Version it (semver on messages), review changes hard, and let everything else evolve behind it.

### Dev environment
- **Containerize everything** (a `Dockerfile` + devcontainer) so "works on my machine" dies. Base off `ros:jazzy` + CUDA for GPU nodes.
- `colcon build --symlink-install`; `pre-commit` with `ament_lint`/`clang-format`/`black`/`ruff`.
- Reference for good ROS 2 project hygiene: [Articulated Robotics](https://articulatedrobotics.xyz/) tutorials and the official [ROS 2 docs](https://docs.ros.org/).

---

## 2. The core contract: WorldModel interface (do this in Week 1–2)

Before any capability, define the messages. A minimal starting sketch (pseudo-`.msg`):

```
# jabas_interfaces/msg/WorldModelSnapshot.msg
std_msgs/Header header              # stamp + frame_id (world frame, e.g. map)
uint64 version                      # monotonically increasing snapshot id
GridLayer traversability            # cost/risk in [0,1] + uncertainty per cell
GridLayer elevation                 # mean height + variance per cell
GridLayer semantics                 # argmax class id + confidence per cell
TrackedObject[] dynamic_objects     # tracks with pose, vel, covariance, class, predicted paths
float32 localization_confidence     # [0,1] from integrity monitor (C7/C9)
```

```
# jabas_interfaces/srv/QueryTraversability.srv
geometry_msgs/Point[] query_points
---
float32[] risk                      # [0,1]
float32[] uncertainty
```

Then provide a **Nav2 costmap plugin** that renders `traversability` into a `costmap_2d`, so your *existing* NavFn+MPPI stack keeps running while you migrate. Plugin base class: `nav2_costmap_2d::Layer`. Reference: [Nav2 costmap plugin tutorial](https://docs.nav2.org/plugin_tutorials/docs/writing_new_costmap2d_plugin.html).

---

## 3. PHASE 0 — Foundations (Months 0–9)

### P0.1 — Record / Replay / Log-driven CI
- **Build on:** `rosbag2` with the **MCAP** plugin ([ros2/rosbag2](https://github.com/ros2/rosbag2), [foxglove/mcap](https://github.com/foxglove/mcap)); **Foxglove** for visualization; **PlotJuggler** for time-series.
- **Steps:**
  1. Standardize logging: `ros2 bag record` MCAP of the canonical topic set (all sensor inputs + all decision outputs + `/tf` + clock). Define this set in `jabas_bringup`.
  2. Write a **replay runner** in `tools/`: launches the node graph with `use_sim_time:=true`, plays a bag, captures outputs to a new bag. Enforce determinism (single-threaded executor for the replayed subsystem, fixed seeds, no wall-clock reads).
  3. Write a **metrics extractor**: reads input+output bags, computes min-obstacle-distance, path length, cmd_vel jerk, intervention flags.
  4. **CI job** (`.github/workflows/replay.yml`): on every PR, replay ~10–20 curated bags in a container, assert metrics within tolerance vs a golden baseline. Fail the PR on regression.
- **Acceptance:** `git push` → CI replays real field logs → a plot of "min distance to obstacle" per scenario is posted to the PR, and a regression fails the build. You can reproduce a named field incident locally with one command.
- **Determinism references:** ROS 2 [executors](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html) + `use_sim_time` docs.

### P0.2 — Safety core + ODD
- **Build on:** your MCU/PLC vendor SDK for the core; ROS 2 side mirrors state. Study the **Simplex/runtime-assurance** pattern and **STPA** (Leveson) for hazard analysis.
- **Steps:**
  1. Write the **ODD document** (where/when/conditions you're allowed to operate). Keep it in the repo.
  2. Implement, on the safety MCU, independent checks: geofence polygon test, v/ω/curvature/slope envelopes, min-distance stop from a *simple* range sensor (not the ML stack), e-stop, heartbeat watchdog on the autonomy SoC.
  3. Define the **command gateway**: all `cmd_vel`/actuator commands pass through the safety core, which clamps or vetoes. The neural stack can never bypass it.
  4. Implement a **safe-stop** fallback trajectory triggered on any monitor trip or heartbeat loss.
- **Acceptance:** kill the main autonomy process mid-drive in sim and on a test rig → robot executes safe-stop within a bounded time, provably, with no operator action. Drive toward the geofence → hard stop at the boundary.
- **Standards to read:** ISO 25119 / ISO 18497 (ag), ISO 26262 + ISO 21448 SOTIF (mental models).

### P0.3 — Simulation + digital twin
- **Build on:** **Gazebo (Harmonic/Ionic)** with `ros_gz` bridge for CI/physics; **NVIDIA Isaac Sim** for photoreal + synthetic data + domain randomization. For nvblox testing there's an [Isaac Sim tutorial](https://nvidia-isaac-ros.github.io/).
- **Steps:**
  1. Model one robot (URDF/SDF) + one field in Gazebo; run the *exact* autonomy stack against it (`use_sim_time`).
  2. Build **replay-driven sim**: feed real logged sensor streams into new software (reuses P0.1) — your highest-value, lowest-cost validation.
  3. Add **procedural field generation** (vary row spacing, crop height, obstacles, lighting) — script it.
  4. Put a smoke-level sim run in CI.
- **Acceptance:** a new planner change is validated across N procedurally-generated fields in CI before it ever touches hardware; every field incident is re-simulated.

### P0.4 — Health signals + telemetry + event triggers
- **Build on:** ROS 2 [`diagnostics`](https://github.com/ros/diagnostics), Prometheus + Grafana, MCAP for clip capture.
- **Steps:**
  1. Every node publishes structured health (localization covariance trace, planner feasibility/cost, perception confidence, comms RTT, CPU/GPU/thermal).
  2. A **health aggregator** node computes a single autonomy-health state.
  3. **Event triggers**: rules (disengagement, near-miss distance, high localization covariance, novel-object flag, operator override) that auto-save a ±N-second MCAP clip and mark it for upload.
  4. Grafana dashboard for fleet health.
- **Acceptance:** the robot autonomously saves and flags its own hard cases; you see fleet health at a glance.

**Phase 0 exit:** data-engine skeleton (log→trigger→clip→replay→sim→CI) + safety core. You can now add ML safely.

---

## 4. PHASE 1 — The Spine (Months 6–18)

### P1.1 — Persistent Semantic Temporal World Model ★
- **Build on:**
  - Geometry/mapping: **[grid_map](https://github.com/ANYbotics/grid_map)** (multi-layer 2.5D grids — elevation, variance, traversability, semantics) and/or **[elevation_mapping](https://github.com/ANYbotics/elevation_mapping)** (robot-centric, handles pose drift).
  - GPU 3D reconstruction: **[nvblox](https://github.com/nvidia-isaac/nvblox)** + **[isaac_ros_nvblox](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox)** — TSDF/ESDF on GPU and **it already ships a Nav2 costmap plugin**, so it doubles as your migration bridge.
  - Tracking: start with a simple GNN/Kalman MOT; grow into JPDA.
- **Steps:**
  1. Stand up `grid_map` layers with **temporal persistence + decay** (fixes Nav2's "forgets obstacles/oscillates" bug immediately — a visible early win).
  2. Add elevation + variance from LiDAR/depth.
  3. Add a **semantics layer** (from P1.2 perception) and a **dynamic-objects layer** (tracks).
  4. Implement the `WorldModelSnapshot` publisher + `QueryTraversability` service + the Nav2 costmap plugin bridge.
- **Acceptance:** existing NavFn+MPPI runs unchanged *through* the world model; toggling temporal persistence measurably reduces oscillation/re-collision in replay.

### P1.2 — Traversability (geometric → learned)
- **Build on:**
  - Geometric: `grid_map` layers (slope from surface normals, roughness = height variance, step = max neighbor diff). `grid_map` explicitly supports a "traversability" layer.
  - Learned self-supervised (the differentiator): **[Wild Visual Navigation (WVN)](https://github.com/leggedrobotics/wild_visual_navigation)** — online self-supervised visual traversability from a few minutes of demonstration; and **[FtFoot](https://github.com/yurimjeon1892/FtFoot)** (self-supervised from footprints, ICRA 2024). Pretraining/eval datasets: **[RELLIS-3D](https://github.com/unmannedlab/RELLIS-3D)** and **RUGD** (off-road semantic).
- **Steps:**
  1. Ship **geometric traversability** first (deterministic, safe, immediate stuck/tip reduction).
  2. Build the **self-supervised label pipeline**: derive slip ratio (`1 - v_actual/v_cmd`), vibration energy (IMU), motor-current spikes from logs → per-cell "how hard was this to drive" labels (Tesla-style auto-labeling, ag-flavored).
  3. Train a BEV/image traversability model (start from WVN's approach); serve via TensorRT.
  4. **Bound the learned model by the geometric safe layer** — learned may add caution, never remove it in safety-critical cases.
- **Acceptance:** measurable drop in stuck/tip incidents vs geometric baseline, in sim and field; learned model degrades gracefully to geometric when uncertain.

### P1.3 — Experience-based field memory ★ (ag moat)
- **Build on:** your own store (this is bespoke — the moat) + `grid_map` georeferenced layers + a cloud sync (Zenoh/MQTT store-and-forward). Conceptual references: E-Graphs (Experience Graphs, Likhachev/Phillips); GP regression for spatial risk (scikit-learn/GPyTorch).
- **Steps:**
  1. Log geo-tagged outcomes (stuck, slip, timing, energy) keyed to field cells + conditions (season, moisture, payload).
  2. Aggregate into a per-field **"trouble heatmap"** (visualize in Foxglove/QGIS).
  3. Serve an **experience cost layer** into the world model / planner; condition on current conditions.
  4. Sync to cloud; aggregate across the fleet so one robot's lesson helps all.
- **Acceptance:** over repeated passes, the robot demonstrably avoids historically-troublesome areas and improves route/timing choices. This is your headline demo.

### P1.4 — Robust localization + confidence
- **Detailed design:** [`12-planar-agricultural-localization-design.md`](12-planar-agricultural-localization-design.md) specifies the planar `map → odom → base_link` contract, temporary RTK commissioning, robot-view and aerial-map localization, learned cross-view features, multi-hypothesis fusion, integrity, and validation.
- **Build on:**
  - Fusion: **[robot_localization](https://github.com/cra-ros-pkg/robot_localization)** (EKF/UKF, GNSS+IMU+odom) to start; graduate to a **[GTSAM](https://github.com/borglab/gtsam)** factor-graph smoother for tight fusion + integrity.
  - GNSS-denied fallback: **[KISS-ICP](https://github.com/PRBonn/kiss-icp)** (parameter-free LiDAR odometry, has a ROS 2 node) and/or **[FAST-LIO2](https://github.com/hku-mars/FAST_LIO)** ([ROS 2 port](https://github.com/Ericsii/FAST_LIO_ROS2)).
  - Relocalization/place recognition: Scan Context (concept) for GNSS-denied recovery.
- **Steps:**
  1. Solid GNSS-RTK + IMU + wheel-odom fusion; publish `/localization/health` (covariance trace + NIS/chi-square innovation test).
  2. Add **innovation gating** to reject GNSS multipath/outliers.
  3. Add **LiDAR-odometry fallback** (KISS-ICP) auto-engaged when GNSS integrity drops.
  4. Map-relative localization against your prior field map (beats row aliasing using the GNSS prior).
- **Acceptance:** induce GNSS dropout in sim/field → localization detects it, switches to LiDAR odometry, and behavior slows rather than drifting silently.

**Phase 1 exit:** a semantic, temporal world model + traversability + field memory + honest localization confidence, replacing the flat costmap — all replayable and safe.

---

## 5. PHASE 2 pointers (Months 15–30) — what to build on

- **Prediction (P2.1):** baselines (constant-velocity + IMM) first; then **[Trajectron++](https://github.com/StanfordASL/Trajectron-plus-plus)** (multimodal, graph-structured, integrates with planning) for people; occupancy-flow for herds. Datasets/patterns from [Waymo Open Motion](https://waymo.com/open/).
- **Prediction/uncertainty-aware MPPI (P2.2):** extend the **[Nav2 MPPI controller](https://github.com/ros-navigation/navigation2/tree/main/nav2_mppi_controller)** with **custom critic plugins** ([MPPI docs](https://docs.nav2.org/configuration/packages/configuring-mppic.html)) that read traversability, predicted occupancy, and uncertainty. This is the cleanest, lowest-risk way to make your existing MPPI dramatically smarter — you keep the controller, add critics.
- **Semantic/human-aware nav (P2.3):** static zones as `grid_map`/costmap layers from the field map; BehaviorTree.CPP ([BehaviorTree.CPP](https://github.com/BehaviorTree/BehaviorTree.CPP)) nodes for "slow near person / stop for animal"; proxemics cost from prediction.
- **Learning costmaps (P2.5):** MaxEnt deep IRL from operator demos; keep it a cost *layer* bounded by safety.

---

## 6. Milestones & sequencing (a realistic Gantt in words)

- **M0–M3:** P0.1 replay-CI MVP + `jabas_interfaces` v0 + world-model skeleton behind a Nav2 costmap plugin. *First visible win: oscillation bug gone via temporal persistence.*
- **M3–M6:** P0.2 safety core + ODD; P0.3 sim + replay-driven sim in CI; P0.4 health signals + event triggers.
- **M6–M9:** P1.1 world model with elevation + semantics + tracks; P1.2 geometric traversability shipped.
- **M9–M12:** P1.4 robust localization + `/localization/health` + LiDAR-odom fallback; P1.3 field-memory heatmaps.
- **M12–M18:** P1.2 learned self-supervised traversability; P1.3 experience cost layer + fleet aggregation (headline demo).
- **M15–M24:** P2.1 prediction baselines→learned; P2.2 prediction/uncertainty-aware MPPI critics.
- **M24–M30:** P2.3 semantic/human-aware nav; P2.5 learning costmaps; begin Phase 3 fleet work.

Re-plan every quarter against reality (per `07`'s cadence). Dependencies: **everything depends on P0.1 (replay) and the `jabas_interfaces` contract.** Do not start ML before both exist.

---

## 7. Build-vs-buy cheatsheet
- **Buy/adopt (don't rebuild):** SLAM/odometry (KISS-ICP, FAST-LIO2, GTSAM), mapping grids (grid_map, nvblox), the local planner core (Nav2 MPPI), logging (MCAP), viz (Foxglove/rerun), sim (Gazebo/Isaac), fusion (robot_localization).
- **Build (your moat):** the `jabas_interfaces` world-model contract, experience/field memory, ag traversability labels + model, semantic farm-rule engine, health/self-healing supervision, fleet experience aggregation, the data-engine loop.
- **Undifferentiated cloud plumbing:** buy/managed where sensible; own the data schema.

See `11-reference-library.md` for the full annotated catalogue of repos, datasets, courses, and papers.
