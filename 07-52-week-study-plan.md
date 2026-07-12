# 07 — The 52-Week Study Plan

**How this is designed.** ~8–10 focused hours/week (you work full-time — see `09` for how). Every week has: **Topics · Reading · Video · Exercise · Project · Outcome · Application**. The plan is *project-anchored*: study feeds directly into the Phase 0/1 projects in `05`, so learning and shipping are the same activity.

**The one rule:** each week you produce one small artifact (code, notebook, doc, or diagram). No artifact = the week didn't happen. Retention comes from building, not reading (see `09`).

**Quarter map:**
- **Q1 (W1–13): Mathematical & estimation foundations + record/replay infra.** Underpins everything; ships P0.1.
- **Q2 (W14–26): Perception, localization, world model.** Ships the spine (P1.1, P1.2, P1.4).
- **Q3 (W27–39): Planning, control, prediction.** Upgrades the planner (P2.1, P2.2).
- **Q4 (W40–52): Learning, safety, fleet, systems & leadership.** Ships safety core, data engine, and sets up Phase 2/3.

Legend for resources refers to `06`.

---

## Quarter 1 — Foundations & Reproducibility (Weeks 1–13)

**W1 — Orientation & the math you'll actually use**
- Topics: linear algebra refresh (vectors, matrices, eigen), why math matters for autonomy.
- Reading: Deisenroth *MML* ch.2–3. · Video: 3Blue1Brown *Essence of Linear Algebra* (all).
- Exercise: implement PCA on a point cloud in NumPy. · Project: set up your learning repo + lab journal; write the "why" of your world-model bet in 1 page.
- Outcome: fluent with the linear-algebra vocabulary. · Application: PCA underpins ground-plane fitting and covariance reasoning in the world model.

**W2 — Probability & Bayes**
- Topics: random variables, Bayes rule, Gaussians, covariance.
- Reading: *MML* ch.6. · Video: 3B1B *Bayes theorem*; StatQuest basics.
- Exercise: 1D Bayes filter in NumPy (predict/update). · Project: document the Bayesian view of the costmap's shortcomings.
- Outcome: think in distributions, not point estimates. · Application: log-odds occupancy update (C1).

**W3 — Calculus, optimization intuition, gradients**
- Topics: gradients, Jacobians, least squares, gradient descent.
- Reading: *MML* ch.5,7. · Video: 3B1B *Essence of Calculus*; Brunton on optimization.
- Exercise: solve a linear least-squares fit by normal equations + by gradient descent. · Project: derive the least-squares pose-fit for wheel-odom calibration.
- Outcome: comfort with optimization as "minimize a cost." · Application: everything from calibration to MPC to IRL.

**W4 — Rigid-body transforms & SE(3)**
- Topics: rotations (SO(3)), homogeneous transforms, quaternions, `/tf`.
- Reading: Barfoot ch.6–7 (Lie groups intro) · *Modern Robotics* ch.3. · Video: Modern Robotics ch.3 lectures.
- Exercise: implement transform composition + quaternion↔rotation-matrix; verify against `tf2`. · Project: audit your robot's `/tf` tree and extrinsic calibration.
- Outcome: never confuse frames again. · Application: the #1 silent bug source in perception/fusion.

**W5 — ROS 2 internals: QoS, executors, lifecycle, composition**
- Topics: DDS, QoS profiles, callback groups, intra-process comms, lifecycle nodes.
- Reading: ROS 2 docs (QoS, executors, composition, lifecycle). · Video: Articulated Robotics ROS 2 series.
- Exercise: build a composable-node graph with intra-process comms; measure latency vs inter-process. · Project: profile your current stack's executor/QoS config; document risks.
- Outcome: you understand the substrate your autonomy runs on. · Application: determinism + hot-path latency for the whole platform.

**W6 — Logging & MCAP/rosbag2 deep dive (P0.1 begins)**
- Topics: rosbag2, MCAP, message schemas, deterministic logging.
- Reading: rosbag2 + MCAP docs. · Video: Foxglove tutorials.
- Exercise: log all topics; open in Foxglove; write a script to extract a time-window clip. · Project: define your canonical "record everything needed to replay" topic set.
- Outcome: you can capture field data properly. · Application: the data-engine substrate (Layer 12/18).

**W7 — Deterministic replay**
- Topics: sources of nondeterminism (threads, wall-clock, RNG, I/O), `use_sim_time`.
- Reading: ROS 2 time docs; determinism discussions. · Video: any ROS 2 sim-time talk.
- Exercise: replay a bag through a node and get identical outputs twice. · Project: a `replay` launch mode for one subsystem.
- Outcome: bit-for-bit replay for one module. · Application: P0.1 core; enables CI + debugging.

**W8 — Visualization & introspection**
- Topics: RViz2, Foxglove, rerun; visualizing world model + decisions.
- Reading: rerun + Foxglove docs. · Video: rerun demos.
- Exercise: build a Foxglove/rerun layout showing costmap + plan + pose + health. · Project: a standard "autonomy debug view."
- Outcome: you can *see* what the robot thinks. · Application: debugging every future capability.

**W9 — Least-squares state estimation & the Kalman filter**
- Topics: KF derivation, prediction/update, tuning Q/R.
- Reading: *Probabilistic Robotics* ch.3 · Barfoot ch.3–4. · Video: Stachniss KF lectures.
- Exercise: implement a KF for a 1D/2D constant-velocity tracker. · Project: KF tracker for a simulated moving obstacle.
- Outcome: KF from first principles. · Application: object tracking in the world model (C1/C4).

**W10 — EKF/UKF & nonlinear estimation**
- Topics: linearization, EKF, UKF, consistency (NEES/NIS).
- Reading: *Probabilistic Robotics* ch.3 · Barfoot ch.4. · Video: Stachniss EKF.
- Exercise: EKF fusing simulated GNSS + odom + IMU heading. · Project: reproduce your `robot_localization` config as a from-scratch EKF; compare.
- Outcome: you understand your localization filter's guts. · Application: P1.4 robust localization (C7).

**W11 — Error-state KF on manifolds**
- Topics: ESKF, error-state on SE(3), IMU integration.
- Reading: Barfoot ch.7–8; Sola "Quaternion kinematics for ESKF" notes. · Video: Stachniss.
- Exercise: ESKF orientation estimation from IMU. · Project: design doc for your target ESKF fusion core.
- Outcome: manifold-correct estimation. · Application: the fusion backbone (C7).

**W12 — Integrity & robust estimation**
- Topics: innovation/chi-square gating, outlier rejection, RAIM/FDE concepts, covariance-as-confidence.
- Reading: RAIM/integrity primer; robust cost functions (Huber). · Video: GNSS integrity talk.
- Exercise: add chi-square measurement gating to W10's EKF; inject GNSS outliers. · Project: define `/localization/health` signal spec.
- Outcome: you can detect a lying sensor. · Application: self-healing localization (C7), health monitoring (C9).

**W13 — Q1 capstone: replay-CI skeleton (ships P0.1 MVP)**
- Topics: consolidate; log-driven regression.
- Exercise: CI job that replays 3 bags and asserts metrics (min-obstacle-distance, path length). · Project: **P0.1 MVP delivered.**
- Outcome: you have a data-engine skeleton. · Application: every future change is now testable on real data. Write a retrospective + refresh the next quarter's plan.

---

## Quarter 2 — Perception, Localization, World Model (Weeks 14–26)

**W14 — Point clouds & geometry**
- Topics: PCL/Open3D, ground segmentation, clustering, voxel grids.
- Reading: Siegwart perception ch. · Video: Stachniss point-cloud lectures.
- Exercise: ground removal + Euclidean clustering on a LiDAR scan. · Project: obstacle clustering node feeding candidate tracks.
- Outcome: raw cloud → objects. · Application: world-model geometry + tracking input.

**W15 — Occupancy & elevation mapping (P1.1 begins)**
- Topics: log-odds occupancy, OctoMap, `grid_map`, elevation with per-cell variance.
- Reading: OctoMap + `grid_map` papers/docs. · Video: ANYbotics `grid_map` talks.
- Exercise: build a rolling elevation map from simulated LiDAR. · Project: `grid_map`-based local map with temporal persistence.
- Outcome: a *remembering* map. · Application: fixes Nav2's "forgets obstacles" bug (C1).

**W16 — Temporal persistence & the world-model API**
- Topics: decay models, static/dynamic split, query interfaces, versioning.
- Reading: re-read `04` C1; BEV occupancy papers (skim). · Video: Tesla AI Day occupancy segment (critical watch).
- Exercise: add decay + a `traversability(cell)` query to your map. · Project: draft the `WorldModelSnapshot` message + query API.
- Outcome: a clean world-model contract. · Application: the spine's interface (C1) — the highest-leverage design you'll make.

**W17 — Deep learning foundations**
- Topics: tensors, autograd, MLPs, training loops, overfitting.
- Reading: *Deep Learning* ch.6; fast.ai lesson 1–2. · Video: Karpathy "Neural Nets: Zero to Hero" (1–2).
- Exercise: train an MLP classifier in PyTorch. · Project: set up training/eval harness + experiment tracking.
- Outcome: you can train and evaluate a model. · Application: all learned components (C3/C4/C6).

**W18 — CNNs & segmentation**
- Topics: convolutions, encoder-decoder, semantic segmentation, metrics (IoU).
- Reading: CS231n notes (CNNs). · Video: CS231n lectures on CNNs.
- Exercise: train a small segmentation net on a public ag/off-road set (e.g., RUGD/RELLIS-3D subset). · Project: surface-class segmentation prototype.
- Outcome: images → semantic masks. · Application: semantic overlay (C1/C8).

**W19 — 3D & BEV perception**
- Topics: PointPillars, Lift-Splat-Shoot, BEV fusion.
- Reading: PointPillars + LSS papers (2-pass). · Video: BEV perception survey talks.
- Exercise: run a pretrained 3D detector; inspect outputs. · Project: design how camera+LiDAR fuse into your BEV world model.
- Outcome: understand modern fused perception. · Application: BEV world-model variant (C1).

**W20 — Traversability, geometric (P1.2 MVP)**
- Topics: slope/roughness/step features from elevation.
- Reading: off-road traversability survey. · Video: field-robotics traversability talks.
- Exercise: compute slope/roughness/step layers in `grid_map`. · Project: **geometric traversability cost layer — P1.2 MVP.**
- Outcome: graded, deterministic traversability. · Application: fewer stuck/tip events (C3).

**W21 — Self-supervised traversability**
- Topics: proprioceptive labels (slip, vibration, current), self-supervision.
- Reading: WayFAST/BADGR-style papers. · Video: off-road learning talks.
- Exercise: derive slip ratio + vibration energy from logged IMU/odom. · Project: auto-label pipeline for traversability from logs.
- Outcome: free labels from driving. · Application: learned traversability (C3), auto-labeling pattern (data engine).

**W22 — SLAM I: LiDAR odometry**
- Topics: ICP, KISS-ICP, LiDAR-inertial odometry.
- Reading: KISS-ICP + FAST-LIO2 papers. · Video: Stachniss ICP/registration.
- Exercise: run KISS-ICP on a bag; evaluate drift. · Project: LiDAR-odom fallback design for GNSS-denied stretches.
- Outcome: odometry without GNSS. · Application: self-healing localization fallback (C7).

**W23 — SLAM II: factor graphs**
- Topics: pose graphs, GTSAM, iSAM2, loop closure.
- Reading: Dellaert & Kaess *Factor Graphs* (skim) + GTSAM tutorials. · Video: Dellaert factor-graph talks.
- Exercise: build a small pose-graph in GTSAM with a loop closure. · Project: prototype GNSS+odom+LiDAR factor-graph fusion.
- Outcome: smoothing-based estimation. · Application: robust fusion core (C7).

**W24 — Map-relative & place recognition**
- Topics: localizing against prior field maps; Scan Context / learned descriptors; row aliasing.
- Reading: Scan Context paper. · Video: place-recognition talks.
- Exercise: implement a simple descriptor + nearest-neighbor relocalization. · Project: design map-relative localization using GNSS prior to beat row aliasing.
- Outcome: recognize "I've been here." · Application: self-healing relocalization (C7), persistent field maps (moat).

**W25 — Multi-object tracking**
- Topics: data association (GNN/JPDA), track lifecycle, IMM.
- Reading: *Probabilistic Robotics* tracking; MOT survey. · Video: MOT tutorials.
- Exercise: multi-target tracker over clustered detections. · Project: dynamic-object layer of the world model.
- Outcome: stable tracks with IDs. · Application: C1 dynamic layer, feeds prediction (C4).

**W26 — Q2 capstone: the spine online (ships P1.1/P1.2/P1.4 MVPs)**
- Exercise: integrate world model (persistent + semantic + tracks + traversability) behind the query API, rendered as a Nav2 costmap plugin; localization health published.
- Project: **Spine MVP delivered**; re-simulate 3 past incidents against it.
- Outcome: the costmap is replaced by a world model. · Application: foundation for all Phase 2 intelligence. Retrospective + replan.

---

## Quarter 3 — Planning, Control, Prediction (Weeks 27–39)

**W27 — Motion planning foundations**
- Topics: configuration space, A*, Dijkstra, sampling (RRT/PRM).
- Reading: LaValle ch.5; Siegwart planning. · Video: Stachniss/CMU planning lectures.
- Exercise: A* and RRT on a 2D grid. · Project: compare global planners on a field map.
- Outcome: planning fundamentals. · Application: route/global planning (Layer 7).

**W28 — Kinodynamic & lattice planning**
- Topics: Dubins/Reeds-Shepp, state lattices, turning constraints (headland turns).
- Reading: LaValle ch.13–14; lattice papers. · Video: motion-planning lectures.
- Exercise: Dubins path generator. · Project: headland-turn planner respecting your platform's turning radius.
- Outcome: feasible curved motion. · Application: coverage/route planning for ag rows.

**W29 — Coverage path planning (ag-critical)**
- Topics: boustrophedon, cellular decomposition, coverage ordering.
- Reading: coverage CPP survey. · Video: CPP talks.
- Exercise: boustrophedon coverage of a polygon field. · Project: field-coverage mission generator.
- Outcome: "cover this field" planning. · Application: mission planning (Layer 7.1).

**W30 — Optimal control & LQR**
- Topics: cost-to-go, LQR, Riccati, discretization.
- Reading: Åström & Murray; Tedrake Underactuated LQR notes. · Video: Brunton *Control Bootcamp*; Tedrake lectures.
- Exercise: LQR for a cart/steering model. · Project: linear tracking controller for your kinematic model.
- Outcome: principled feedback control. · Application: trajectory tracking (Layer 8).

**W31 — Model Predictive Control**
- Topics: receding horizon, QP formulation, constraints.
- Reading: Borrelli/Bemporad/Morari (intro chapters). · Video: Brunton MPC; Tedrake trajectory opt.
- Exercise: implement a simple MPC (via a QP solver) for path tracking. · Project: MPC vs pure-pursuit comparison in sim.
- Outcome: constrained optimal control. · Application: control layer + MPPI understanding.

**W32 — MPPI in depth**
- Topics: information-theoretic MPC, sampling, cost design, GPU parallelism.
- Reading: Williams et al. MPPI papers; Nav2 MPPI controller source. · Video: MPPI talks.
- Exercise: implement toy MPPI; then read Nav2's critics. · Project: map Nav2 MPPI critics to world-model layers.
- Outcome: you own your local planner. · Application: P2.2 prediction-aware MPPI (C5).

**W33 — Prediction I: baselines**
- Topics: constant-velocity, IMM, evaluation (ADE/FDE).
- Reading: prediction survey; Trajectron++ (skim). · Video: Waymo prediction talks.
- Exercise: CV + IMM predictor over tracks; compute ADE/FDE. · Project: **prediction baseline into world model — P2.1 MVP.**
- Outcome: forecasts with metrics. · Application: prediction-aware planning (C4/C5).

**W34 — Prediction II: learned & occupancy-flow**
- Topics: multimodal prediction (CVAE/graph), occupancy-flow for herds.
- Reading: VectorNet/Trajectron++ + occupancy-flow papers. · Video: Waymo Sim Agents talks.
- Exercise: train a small multimodal predictor on a public set. · Project: occupancy-flow design for livestock.
- Outcome: distributional, scene-aware prediction. · Application: safe behavior near people/herds (C4).

**W35 — Prediction-aware & risk-aware planning (P2.2)**
- Topics: time-varying costs, chance constraints, CVaR, freezing-robot problem.
- Reading: risk-aware planning papers. · Video: uncertainty-in-planning talks.
- Exercise: add predicted-occupancy + uncertainty inflation to MPPI critics. · Project: **prediction/uncertainty-aware MPPI — P2.2 MVP.**
- Outcome: plans that respect the future and your confidence. · Application: measurably safer, smoother (C5).

**W36 — Behavior trees & decision-making**
- Topics: BTs (Nav2), when BTs break down, state machines vs BTs.
- Reading: *Behavior Trees in Robotics and AI* (Colledanchise & Ögren, free). · Video: BT.CPP talks.
- Exercise: build a BT with health-aware branches (slow/stop/escalate). · Project: health-reactive behavior layer.
- Outcome: inspectable decision logic. · Application: behavior planning + graceful degradation (C9).

**W37 — Semantic & human-aware navigation (P2.3)**
- Topics: semantic costs, geofenced zones, proxemics.
- Reading: human-aware navigation survey. · Video: social-navigation talks.
- Exercise: static keep-out/speed zones + "stop for person." · Project: **semantic-zone navigation — P2.3 MVP.**
- Outcome: meaning-driven behavior. · Application: crop/zone/people rules (C8).

**W38 — Learning to plan / IRL (intro)**
- Topics: imitation learning, DAgger, MaxEnt IRL.
- Reading: Ziebart MaxEnt IRL; DAgger paper. · Video: RL/IRL lectures (Levine's Deep RL course, IRL lectures).
- Exercise: learn cost-term weights from demonstrated paths. · Project: demo-tuned cost vs hand-tuned, in replay.
- Outcome: cost from demonstrations. · Application: learning costmaps (C6).

**W39 — Q3 capstone: intelligent local planning**
- Exercise: integrate prediction + risk-aware MPPI + semantic zones + health-reactive BT.
- Project: full Phase-2 planning demo in sim + limited field; re-simulate incident library.
- Outcome: the robot understands, predicts, and plans with risk. · Application: Phase 2 milestone. Retrospective + replan.

---

## Quarter 4 — Learning Systems, Safety, Fleet, Leadership (Weeks 40–52)

**W40 — Reinforcement learning foundations**
- Topics: MDPs, value/policy iteration, Q-learning, policy gradients.
- Reading: Sutton & Barto ch.3–6,13. · Video: David Silver RL course / Levine Deep RL.
- Exercise: tabular Q-learning on gridworld; then a simple policy-gradient. · Project: frame one ag behavior as an MDP (don't train it in prod — understand it).
- Outcome: RL literacy. · Application: offline RL / residual control awareness (frontier).

**W41 — MLOps for robotics I: data**
- Topics: dataset versioning, curation, active learning, auto-labeling.
- Reading: Chip Huyen *Designing ML Systems* (data ch.). · Video: MLOps talks; Tesla auto-labeling segment.
- Exercise: version a dataset with DVC; build an active-learning trigger (uncertainty-based). · Project: data-engine dataset pipeline design.
- Outcome: disciplined data flow. · Application: continuous learning (Layer 13, P3.1).

**W42 — MLOps for robotics II: models**
- Topics: registry, TensorRT/ONNX, quantization, shadow/A-B, drift monitoring.
- Reading: TensorRT + Triton docs; Huyen deployment ch. · Video: model-serving talks.
- Exercise: export a model to ONNX/TensorRT; benchmark on Orin (or desktop GPU). · Project: model-serving + shadow-mode design.
- Outcome: safe model deployment. · Application: AI integration (Layer 15), P3.1.

**W43 — Simulation & digital twins (P0.3 deepening)**
- Topics: Isaac Sim / Gazebo, sensor sim, domain randomization, replay-driven sim.
- Reading: Isaac Sim docs; domain-randomization papers. · Video: Isaac Sim tutorials.
- Exercise: run your stack in sim on a procedural field. · Project: replay-driven-sim harness (real sensors → new code).
- Outcome: validate before field. · Application: sim/digital twin (Layer 14).

**W44 — Functional safety & the safety core (P0.2)**
- Topics: HARA, ODD, SOTIF, Simplex/runtime assurance, ISO 25119/18497.
- Reading: ISO 26262/21448 primers; Leveson STPA (intro). · Video: functional-safety talks; STPA intro.
- Exercise: write a HARA-lite for one hazard (person in path). · Project: **safety-core spec + ODD document — P0.2 design.**
- Outcome: you think in safety cases. · Application: the deterministic safety core (Layer 9).

**W45 — Real-time & high-performance C++**
- Topics: RT scheduling, lock-free basics, cache/perf, `PREEMPT_RT`.
- Reading: *Effective Modern C++* (key items); *C++ Concurrency in Action* (skim). · Video: CppCon real-time talks.
- Exercise: profile + optimize a hot node; measure jitter under RT kernel. · Project: RT design for control/safety loop.
- Outcome: production-grade C++/RT instincts. · Application: control + safety core performance.

**W46 — GPU computing**
- Topics: CUDA model, memory, kernels; where to GPU-accelerate.
- Reading: Kirk & Hwu (intro); CUDA docs. · Video: NVIDIA CUDA tutorials.
- Exercise: write a simple CUDA kernel (e.g., cost-grid op); or GPU-accelerate MPPI rollouts. · Project: identify your stack's GPU-acceleration targets.
- Outcome: GPU literacy. · Application: perception + MPPI performance.

**W47 — Distributed systems & cloud**
- Topics: data-intensive systems, streaming, storage, Zenoh for robot↔cloud.
- Reading: Kleppmann *DDIA* (ch.1–4,11). · Video: DDIA talks; Zenoh talks.
- Exercise: store-and-forward uploader over simulated intermittent link. · Project: cloud data-ingestion + map/experience service design.
- Outcome: fleet/cloud architecture literacy. · Application: cloud infra (Layer 11), fleet (C10).

**W48 — Fleet intelligence & multi-robot**
- Topics: map merging, task allocation, MAPF/deconfliction, federated learning.
- Reading: CBS + MAPF survey; VDA5050 overview. · Video: multi-robot talks.
- Exercise: Hungarian task-allocation; 2-robot deconfliction in sim. · Project: fleet-manager + shared-experience design.
- Outcome: fleet-first thinking. · Application: C10, Phase 3.

**W49 — Navigation health & self-healing (C9/C7 synthesis)**
- Topics: runtime monitors, OOD detection, conformal prediction, graceful degradation.
- Reading: runtime-assurance + OOD papers; conformal-prediction intro. · Video: monitoring talks.
- Exercise: OOD detector on perception features; health→speed policy. · Project: navigation-health-monitor node design.
- Outcome: predict degradation before failure. · Application: C9, self-healing (C7).

**W50 — Foundation models & AI copilots (frontier literacy)**
- Topics: VLMs (open-vocab), VLA policies, LLM agents/RAG for operators.
- Reading: SAM/Grounding-DINO/CLIP + a VLA survey; RAG basics. · Video: recent CoRL/robot-foundation-model talks.
- Exercise: open-vocab detection on field images; a RAG prototype over your docs/logs. · Project: operator-copilot design (advisory, grounded, out of safety path).
- Outcome: informed frontier judgment. · Application: C11, Phase 4 bets — know what to adopt vs defer.

**W51 — Systems engineering, leadership, product**
- Topics: eng leadership, org/team design, product thinking, roadmapping, KPIs.
- Reading: Larson *Staff Engineer* + Fournier *Manager's Path* (key chapters); Cagan *Inspired* (skim). · Video: staff-eng / eng-leadership talks.
- Exercise: write your team's technical strategy on one page; define your top-5 autonomy KPIs. · Project: a 12-month team roadmap tied to `05` phases.
- Outcome: you lead the platform, not just build it. · Application: `08` evolution path; how you scale beyond yourself.

**W52 — Capstone & year review**
- Topics: consolidate; plan year 2.
- Exercise: write a technical white paper: "JABAS Autonomy Platform — architecture, moat, and 3-year plan" (this is your CTO artifact — use it for the board, hiring, investors).
- Project: demo of the integrated Phase-0/1/2 MVPs; publish an internal tech talk.
- Outcome: you can articulate and defend a full autonomy-platform vision. · Application: everything. Then re-derive year 2's 52 weeks from the current state of `05`.

---

## Cadence rules
- **Weekly:** 1 concept block + 1 build block + 1 artifact. Review last week's artifact for 15 min (spaced repetition).
- **Monthly:** a "connect-the-dots" day — no new material, only integrate what you learned into the platform docs.
- **Quarterly:** retrospective + replan the next 13 weeks against `05`'s current reality. The plan is a living document, not a contract.
- **When behind:** drop the video and reading, keep the exercise. Building > consuming (see `09`).

Next: `08-personal-mastery-and-evolution.md`.
