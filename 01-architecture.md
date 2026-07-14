# 01 — The Complete Autonomy Stack Architecture (Sensors → Cloud)

This is your architectural bible. It describes the *target* platform. You will not build it all at once; `05-flagship-projects.md` sequences it. Read this to understand how the pieces fit and *why* the boundaries are where they are.

## Design tenets (the "constitution")

1. **World model at the center.** Perception writes to it; planning reads from it. Modules never wire directly to each other's internal state.
2. **Two clocks, two trust levels.** A hard real-time, deterministic **safety + control core** (C++, bounded latency) and a softer real-time **intelligence layer** (perception, prediction, planning, some ML). The intelligence layer *advises*; the safety core *decides* what is allowed.
3. **Everything timestamped in one clock domain.** Hardware-timestamped sensors, PTP/`chrony` sync, a single `/tf` tree, and a consistent time source. Most "AI" bugs in robotics are actually time-sync bugs.
4. **Record-everything bus.** Every message needed to replay a decision is logged with deterministic ordering. Replay is a first-class runtime mode.
5. **Edge-cloud symmetry.** The same code runs on the robot, in replay, and in sim. No "sim-only" or "cloud-only" forks of core logic.

---

## Layer 0 — Compute, OS, middleware, time

- **Compute topology.** Typically: (a) a real-time-capable MCU/safety PLC for the safety core and motor interface; (b) an x86 or Jetson-class GPU SoC (Orin) for perception + planning; optionally (c) a second GPU for heavy ML. Ag advantage: you have power and payload budget a drone/car doesn't — use it.
- **OS.** Ubuntu + `PREEMPT_RT` kernel for the planning/perception box; a genuine RTOS or safety PLC (e.g., IEC 61508-rated) for the safety core. Do not run your e-stop logic in a ROS node on a non-RT kernel.
- **Middleware.** ROS 2 with a **carefully chosen DDS** (Cyclone DDS or Zenoh-DDS bridge). Understand QoS deeply — reliability, durability, history depth. Use **composable nodes / intra-process comms** to avoid serialization on the hot path. Consider **Zenoh** for robot↔cloud and multi-robot links (it is becoming the ROS 2 answer for lossy/WAN transport).
- **Time.** PTP (IEEE 1588) or GPS-disciplined clock across sensors; `use_sim_time` discipline; hardware trigger lines for camera/LiDAR sync where possible.
- **Determinism.** Prefer a controlled executor (single-threaded or a well-understood multithreaded executor with callback groups). Random seeds, message ordering, and I/O all matter for replay.

**Key idea:** middleware and time are "boring" and are where most production autonomy programs quietly bleed reliability. Invest here early.

---

## Layer 1 — Sensors

Agricultural sensing suite (typical, tiered):
- **GNSS-RTK / RTK-GPS + dual-antenna heading.** Open sky is your friend — cm-level position and true heading. This is a superpower road AVs mostly lack. Budget for RTK corrections (NTRIP/base station) and dead-reckoning through canopy/tree occlusion.
- **IMU (tactical-grade if budget allows).** For attitude, dead reckoning, and terrain slope. Ag terrain is bumpy; a good IMU + wheel odometry + GNSS fusion is your localization backbone.
- **Wheel/track odometry + steering encoders.** Watch for wheel slip on mud/loose soil — model it.
- **LiDAR (3D spinning or solid-state).** Geometry, obstacles, row structure, terrain. Dust and crop occlusion are real challenges.
- **Cameras (multi, global-shutter, HDR).** Semantics: crop vs weed vs person vs animal, row detection, ground type. Consider stereo for cheap depth and mono-depth as backup.
- **Radar (mmWave).** Robust in dust/rain/fog where LiDAR/camera struggle — a differentiator in dusty fields.
- **Thermal camera.** Humans/animals in crops, night operation, engine/hotspot detection.
- **Microphones / current sensors / temperature.** For health monitoring and diagnostics (bearing wear, motor faults).

**Principles:** hardware-timestamp everything; calibrate intrinsics *and* extrinsics rigorously (this is the #1 silent perception killer); design for **graceful degradation** — the system must state which sensors it trusts right now and adapt.

---

## Layer 2 — Perception

Goal: turn raw sensor streams into **detections, semantics, and geometry** with uncertainty.

- **Low-level geometry:** point-cloud processing (ground segmentation, clustering), stereo/mono depth, ego-motion.
- **Semantic perception:** 2D/3D semantic + instance segmentation (crop rows, weeds, people, animals, machinery, poles, wires, water, mud), object detection & tracking.
- **Traversability:** the ag-critical output — a per-cell/patch estimate of "can I safely drive here and at what cost?" fusing geometry (slope, roughness, step height) and semantics (this is crop I must not crush / this is a ditch / this is mud that will bog me).
- **Sensor fusion:** early (BEV feature fusion) vs late (fuse detections). Trend is **BEV (bird's-eye-view) fusion** — project camera + LiDAR + radar features into a common top-down grid, which is exactly the representation planning wants.
- **Uncertainty:** every output carries covariance/confidence. Downstream planning must consume uncertainty, not point estimates.

**Architecture:** perception nodes are GPU-heavy, run at sensor rate, and publish into the world model — never directly to the planner. Use a model-serving layer (TensorRT/ONNX Runtime) decoupled from ROS node lifecycle so you can hot-swap models.

**Ag-specific hard problems:** deformable/self-similar environments (every row looks alike → aliasing in localization & perception), extreme lighting, dust/mud, seasonal appearance change (the same field looks completely different in April vs August). Your data engine must capture seasonal diversity.

---

## Layer 3 — Localization

- **Backbone by product profile:** an RTK-equipped product uses tightly-coupled **GNSS-RTK + IMU + wheel odometry** fusion for drift-free metric pose in open field. The **no-runtime-RTK profile** in [`12-planar-agricultural-localization-design.md`](12-planar-agricultural-localization-design.md) uses RTK only for commissioning/validation, then runs on LIO + wheel odometry + map-relative localization, with ordinary GNSS only as a coarse prior.
- **LiDAR/visual odometry & SLAM** for GNSS-denied stretches (under tree canopy, in barns, near tall structures): LIO-SAM / FAST-LIO2 / KISS-ICP style LiDAR-inertial odometry; visual-inertial (VINS-Fusion, ORB-SLAM3) as complement.
- **Map-relative localization:** localize against your *own prior map* of the field (from previous passes) — a huge ag advantage since you revisit fields. This enables "the tree is here again" recognition and centimeter repeatability for row-following.
- **Self-healing localization (differentiator):** continuous integrity monitoring — detect GNSS multipath/spoofing, RTK dropout, wheel slip, and *automatically reconfigure the fusion* (drop bad sensors, switch to LiDAR odometry, trigger relocalization). See `04` for the capability deep dive and [`12-planar-agricultural-localization-design.md`](12-planar-agricultural-localization-design.md) for the implementable `(x,y,yaw)` aerial-map/RTK-commissioning design.

**Math foundations:** state estimation on manifolds (SO(3)/SE(3)), EKF/ESKF, factor-graph smoothing (MAP inference, iSAM2), consistency & observability, robust cost functions (Huber, switchable constraints).

---

## Layer 4 — Mapping & Semantic Mapping

- **Geometric maps:** persistent 2.5D/3D — elevation maps, TSDF/OctoMap/voxel, or **implicit/neural maps** (research edge). For ag, a **georeferenced field map** (rows, headlands, obstacles, terrain) that persists across sessions is central.
- **Semantic maps:** annotate the geometry — "row 14," "gate," "irrigation pipe," "known muddy patch," "beehive keep-out," "steep bank." This is what turns navigation from geometric to *meaningful*.
- **Topological/route graph:** fields → blocks → rows → headlands → paths, as a graph for mission and route planning. This is how you plan "cover this field" rather than "go to XY."
- **Map lifecycle:** maps are versioned artifacts in the cloud, updated by the fleet, validated, and served back. Change detection ("the gate moved," "new obstacle since last week") is a first-class feature.

**Ag advantage:** persistent, improving field maps built from repeated visits are a moat road AVs can't easily replicate at the per-property level.

---

## Layer 5 — World Model & Dynamic Environment Representation

This is the platform's heart (see README principle #1).

- **What it is:** a single, queryable, probabilistic, *temporal* fused representation combining static map + semantics + currently-perceived geometry + tracked dynamic agents + uncertainty. Everything else queries it: "is cell X traversable?", "where will that person be in 3 s?", "what is the cost of this path?"
- **Static + dynamic split:** static/semi-static layers (terrain, crop rows, structures) vs dynamic layer (people, animals, vehicles, other robots) with tracking and short-horizon memory.
- **Temporal coherence:** objects persist through occlusion; the model has memory (Nav2's costmap does not — it forgets, causing oscillation and re-collision with just-seen obstacles).
- **Representations to know:** occupancy/elevation grids → BEV grids → object-centric graphs → **learned latent world models** (research: PredNet/Dreamer-style, occupancy-flow, neural fields). Production today: layered BEV + object tracks + semantic map. The bet for years 3–5: partly-learned world models.
- **Uncertainty & queryability:** expose a clean API — geometric queries, semantic queries, prediction queries — so planners are decoupled from representation internals.

---

## Layer 6 — Prediction

- **What:** forecast the future state of dynamic agents (humans, animals, livestock, other machines) and of the environment (this mud is spreading, dust cloud from that tractor).
- **Methods:** physics/constant-velocity baselines → intention/maneuver models → learned multimodal trajectory prediction (social-LSTM, Trajectron++, VectorNet/graph, Transformer-based) → **occupancy-flow** (predict future occupancy grids, robust when you can't enumerate agents — great for herds/flocks).
- **Ag specifics:** fewer adversarial actors than city driving, but *animals* are erratic and *workers* move unpredictably around machinery. Predict conservatively; couple tightly to safety.
- **Math:** probabilistic time-series, mixture models (predict distributions, not single futures), graph neural nets, sequence models; proper scoring (minADE/minFDE, NLL, calibration).

---

## Layer 7 — Planning (four nested layers)

Modern stacks separate planning into a **hierarchy**, each at its own rate/horizon:

1. **Mission planning (minutes–hours):** "cover field 7, avoid the wet SW corner, refill at the road at 40% battery." Coverage-path-planning, task allocation, scheduling, energy/time optimization. Often cloud-assisted, fleet-aware.
2. **Behavior planning (seconds):** the *decision* layer — follow row, turn at headland, yield to human, stop for animal, request help. Today: Behavior Trees (Nav2 BT). Evolution: BTs + learned policies + a "decision" module that reasons over the world model. Keep it inspectable.
3. **Route planning (seconds):** graph search over the topological/route map — which rows, which order, which headland turns (Dubins/Reeds-Shepp for turning constraints, coverage ordering).
4. **Trajectory/motion planning (10–50 Hz):** kinodynamic local planning producing feasible, smooth, safe trajectories. Today: MPPI (you have it), TEB, or lattice. Evolution: MPPI/MPC with **learned costmaps + prediction-aware costs + traversability**, and optionally learned proposals.

**Key upgrade vs. vanilla Nav2:** planning consumes the *world model + prediction + semantics + experience*, not a flat costmap. And the layers share a consistent cost semantics.

---

## Layer 8 — Control

- **Trajectory tracking:** MPC (linear/nonlinear) or well-tuned pure-pursuit/Stanley for row following; torque/traction control for slip; actuator allocation for skid-steer/Ackermann/articulated platforms.
- **Vehicle & terrain models:** slip, tire-soil interaction (terramechanics!), load, slope. Ag control is dominated by **traction and slip on deformable terrain** — a rich, under-served area.
- **Math:** MPC (QP/NLP), Lyapunov stability, system ID, adaptive/robust control, optionally learning-based control (residual RL, MPC + learned dynamics).
- **Safety coupling:** control commands pass through the safety core's envelope check before reaching actuators.

---

## Layer 9 — Safety (the deterministic core)

- **Independent safety core:** geofence enforcement, velocity/acceleration/curvature envelopes, minimum-distance collision guard, tip-over/slope limits, e-stop, remote-stop, heartbeat/watchdogs, safe-stop trajectories. Simple, auditable, ideally on separate certified hardware.
- **Runtime monitors / safety cases:** the learned stack proposes; the safety core disposes. Runtime assurance (Simplex architecture): a verified fallback controller takes over if monitors trip.
- **Standards to learn:** ISO 25119 / ISO 18497 (ag machinery safety & autonomy), ISO 26262 (automotive functional safety — the mental model), SOTIF/ISO 21448 (safety of the intended function — crucial for ML that is "correct but insufficient"), ISO 3691-4 (industrial trucks). You don't need full certification day one, but architect *toward* it.
- **Principle:** never let a neural net directly command actuators without a deterministic guard. This is how you deploy ML in the field and sleep at night.

---

## Layer 10 — Fleet Management

- **Fleet orchestration:** assign robots to fields/tasks, schedule, load-balance, handle refuel/recharge, coordinate shared resources (gates, roads, charging).
- **Multi-robot coordination:** deconfliction, formation/coverage splitting, shared world-model/map merging, communication under poor connectivity.
- **Teleoperation & assisted autonomy:** an operator supervises N robots, gets escalations ("I'm stuck / I see something I don't understand"), and can teleop or annotate. Design the human-in-the-loop economics early — it's how you scale before full autonomy.
- **Standards/inspiration:** VDA5050 (AGV/AMR fleet interface) is worth knowing even if you adapt it.

---

## Layer 11 — Cloud Infrastructure

- **Ingestion:** interesting-event and log uploads over intermittent rural connectivity (store-and-forward, prioritized, bandwidth-aware; Zenoh shines here).
- **Data lake + catalog:** raw + processed sensor data, indexed and queryable ("find all times a person appeared within 3 m in mud").
- **Services:** map service, mission service, model registry, fleet management, OTA update, remote assist, dashboards.
- **Infra:** Kubernetes, object storage, a stream processor, a time-series DB for telemetry, and a **robotics-aware data platform** (rosbag2/MCAP-native tooling). Consider managed robotics/data platforms vs. build — but own the schema.
- **Security:** signed OTA, secure boot, per-robot identity/PKI, encrypted comms, over-the-air rollback. Farms are targets too.

---

## Layer 12 — Data Collection & the Data Engine

The flywheel (README principle #2), concretely:
1. **Log everything replayably** (MCAP/rosbag2) with health/telemetry.
2. **Triggers on the edge** detect "interesting" events (disengagement, near-miss, high uncertainty, prediction error, novel object, operator override) and upload just those clips — you can't upload everything from a field.
3. **Auto-labeling + human-in-the-loop labeling** (offboard "big models" label data for onboard "small models" — Tesla's auto-labeling pattern).
4. **Dataset curation & versioning** (DVC/lakeFS-style), balanced across seasons/fields/conditions.
5. **Training + evaluation** with regression suites.
6. **Sim validation** before deploy.
7. **OTA deploy + fleet A/B/shadow mode.**
8. Repeat. **Measure cycle time of this loop — it is your most important internal KPI.**

---

## Layer 13 — Continuous Learning

- **Shadow mode & A/B:** run new models alongside production, compare, don't act, gather evidence.
- **Active learning:** the fleet *chooses* what data to label based on uncertainty/novelty/disagreement — the highest-leverage way to spend labeling budget.
- **Regression & validation gates:** no model ships without passing sim + replay + metric gates. Prevent silent regressions.
- **Fleet learning:** aggregate rare events across the whole fleet so every robot benefits from every robot's mistakes.

---

## Layer 14 — Digital Twins & Simulation

- **Simulation tiers:** (a) fast headless kinematic/dynamic sim for planning/CI (thousands of runs); (b) high-fidelity physics + photoreal sensor sim for perception (Isaac Sim / Gazebo / custom); (c) **replay-driven sim** (feed real logged sensor data through new software — the highest-value, lowest-cost validation).
- **Digital twin:** a live, data-backed virtual model of a specific robot and field — for what-if planning, predictive maintenance, and operator situational awareness. Ag twin = the field + crop growth model + machine state.
- **Sim-to-real:** domain randomization, sensor-model calibration, and *closing the loop* by validating sim predictions against field outcomes. Beware over-trusting sim for perception; trust it more for planning/control logic.
- **Procedural field generation:** generate endless synthetic fields (row layouts, crops, obstacles, weather) for coverage of the long tail.

---

## Layer 15 — AI Integration

- **Where ML lives:** perception (most), prediction (much), traversability/costmaps (increasingly), planning proposals (some), diagnostics/analytics (much), operator copilots (LLM/VLM).
- **Model-serving discipline:** versioned models in a registry, TensorRT/ONNX runtime, quantization/pruning for edge, A/B & shadow, monitored for drift.
- **Foundation models (the year 4–5 bet):** VLMs for open-vocabulary perception & scene understanding ("is that a child or a scarecrow?"), robotics foundation models / VLA (vision-language-action) for generalist behavior, LLM copilots for operators and for your own engineering (log triage, incident summaries). Adopt selectively; keep them out of the safety path.

---

## Layer 16 — Analytics

- **Operational analytics:** coverage, throughput, energy/acre, downtime, disengagements/interventions per hour, MTBF, cost/acre. These are the numbers the *business* runs on — own them.
- **Autonomy analytics:** where/why the robot struggles, geospatial heatmaps of interventions, model performance by condition/season/field.
- **Agronomic analytics (upside):** your robots are also a *sensing network* — crop health, weed maps, yield prediction. This is a second product hiding in your platform.

---

## Layer 17 — Monitoring & Observability

- **Health monitoring:** per-subsystem health, sensor integrity, localization integrity, compute/thermal, comms quality — with a single "autonomy health" state the robot and operator can trust.
- **Navigation health monitoring (differentiator):** detect degraded autonomy *before* failure (rising uncertainty, planner struggling, perception confidence dropping) and degrade gracefully / request help.
- **Observability stack:** structured logs, metrics (Prometheus/Grafana), distributed tracing across nodes, alerting. Treat the robot like a distributed system in production (because it is).

---

## Layer 18 — Replay Systems

- **Deterministic record/replay:** re-run the exact software on exact logged inputs and get exact outputs. This is the foundation of debugging, CI, and regression testing for autonomy.
- **Log-driven CI:** every code change replays against a library of "golden" and "failure" logs; metrics gate merges.
- **Interactive replay/debugging:** scrub time, visualize world model + decisions (Foxglove/rerun/RViz), compare "what it did" vs "what a new version would do" on the same log.

---

## How the layers talk (interface contracts)

- Perception/localization → **World Model** (write).
- World Model → Prediction, Planning, Monitoring (read, versioned queries).
- Prediction → World Model (dynamic layer) + Planning.
- Planning (mission→behavior→route→trajectory) → Control.
- Control → **Safety Core** → actuators.
- Everything → **Record bus** → Cloud → Data engine → back to models/maps/missions.

Define these as **stable, versioned message contracts** early. The single best architectural decision you can make is fixing the world-model interface so you can evolve everything behind it.

Next: [`02-industry-analysis.md`](02-industry-analysis.md) — how the leaders actually build this and what to steal.
