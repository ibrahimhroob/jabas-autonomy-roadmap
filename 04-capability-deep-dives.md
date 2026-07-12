# 04 — Capability Deep Dives

Each capability follows the same template:
**Why valuable · Theory · Math · Algorithms · Software architecture · Implementation strategy · ROS 2 integration · Performance · Pitfalls · Open research.**

Notation: poses on SE(3), states `x`, controls `u`, measurements `z`, belief `bel(x)=p(x|z_{1:t},u_{1:t})`.

---

## C1 — Persistent Semantic Temporal World Model

**Why valuable.** It is the platform's spine (README #1). Replaces the memoryless costmap; gives every downstream module a coherent, uncertain, temporal, semantic view. Enables prediction, semantic behavior, experience, and analytics.

**Theory.** A world model is a *recursive Bayesian estimate* of the environment state (static + dynamic + semantic) conditioned on all sensor history and the map prior. Static structure is estimated by mapping (SLAM/occupancy); dynamic structure by multi-object tracking; semantics by learned classifiers; all fused with explicit uncertainty and temporal persistence (memory through occlusion).

**Math.**
- Occupancy per cell via log-odds: `l_t = l_{t-1} + log(p(m|z_t)/(1-p(m|z_t))) - l_0` (standard inverse-sensor-model update).
- Elevation/terrain as a Gaussian per cell (mean height, variance) with Kalman update on new measurements.
- Dynamic objects: Bayesian tracking, `bel(x_t)=η p(z_t|x_t)∫p(x_t|x_{t-1})bel(x_{t-1})dx_{t-1}`.
- Semantics: per-cell/object class posterior `p(c|features)` from a network, fused over time by recursive Bayes or Dempster–Shafer.
- Data association: MHT/JPDA; gating with Mahalanobis distance.

**Algorithms.** Occupancy/elevation mapping (OctoMap, `grid_map`, nvblox TSDF), Bayesian tracking (Kalman/UKF + global nearest neighbor / JPDA / MHT), semantic segmentation nets, temporal fusion (Bayesian filtering per layer), BEV feature fusion for the learned variant.

**Software architecture.** A **layered store**: (1) static semantic map (from cloud, versioned), (2) local geometric layer (elevation/occupancy, rolling window around robot), (3) dynamic-object layer (tracks), (4) semantic overlay. A **query API**: `traversability(cell)`, `objects_in(region)`, `semantic_at(cell)`, `predict(object,Δt)`, each returning value + uncertainty. Writers = perception/localization; readers = planning/prediction/monitoring. Keep representation internals private behind the API.

**Implementation strategy.** Start by wrapping Nav2's costmap as one *read view* of a richer store, so you can migrate incrementally. Build on `grid_map` + a tracking library + your semantic net. Add temporal persistence first (fix the "forgets obstacles" bug) — instant, visible win. Then semantics, then the learned BEV variant.

**ROS 2 integration.** Implement as a lifecycle-managed component with intra-process comms. Publish a `WorldModelSnapshot` (versioned, timestamped) and offer services/actions for queries. Provide a Nav2 `costmap_2d` plugin that renders the world model into a costmap so existing planners keep working during migration.

**Performance.** Rolling-window local map (bounded memory); GPU for BEV/TSDF (nvblox); avoid per-cycle full-map serialization — use shared memory / intra-process; target world-model update at sensor rate (10–20 Hz) with query latency < 5 ms.

**Pitfalls.** Time-sync errors corrupt fusion (ghost obstacles); over-persistent memory (stale obstacles never cleared) vs under-persistent (forgetting) — tune decay carefully; unbounded map growth; mixing frames; trusting semantics without uncertainty.

**Open research.** Fully learned/neural world models; occupancy-flow as unified static+dynamic; open-vocabulary semantic mapping; long-horizon memory; uncertainty calibration in learned maps.

---

## C2 — Experience-Based Planning / Field Memory

**Why valuable.** Your single biggest ag-specific moat. You drive the same fields repeatedly; remembering outcomes ("SW corner bogs in spring," "this headland turn is smooth," "gate 3 is often open") compounds into reliability competitors can't match without your field-hours.

**Theory.** Learning from repeated traversal = experience graphs + case-based reasoning + reinforcement-from-outcomes. Formally: augment planning cost with a learned residual `c(x) = c_prior(x) + c_experience(x)`, where `c_experience` is estimated from historical outcomes at that location/condition. Related: E-Graphs (Experience Graphs) bias search toward previously successful paths; Lifelong/continual learning updates the estimate.

**Math.**
- Outcome model per location & condition: `E[risk | cell, season, moisture, payload]` via Gaussian-process regression or a learned table with uncertainty.
- Experience graph reuse: shortest path with edge cost reduced along reused edges: `g(e)=min(c(e), ε·c(e)+reuse_bonus)`.
- Bayesian updating of per-cell success probability with Beta priors: `Beta(α+successes, β+failures)`.

**Algorithms.** E-Graphs / experience-based A* & sampling planners; GP regression for spatial risk; Thompson sampling for explore/exploit on uncertain routes; map-matching to align experiences across passes.

**Software architecture.** A **field-experience store** in the cloud keyed by georeferenced cells + conditions, synced to the robot as a prior layer of the world model. A component that (a) logs outcomes (slip events, stuck events, timing, energy), (b) aggregates per cell/condition, (c) serves an "experience cost layer" to planning.

**Implementation strategy.** Phase 1: log geo-tagged outcomes and visualize a "trouble heatmap" per field. Phase 2: feed a static experience cost layer into the planner. Phase 3: condition on season/weather/payload; add explore/exploit. Phase 4: fleet-wide sharing (every robot benefits).

**ROS 2 integration.** Experience cost as a `costmap_2d` layer plugin or a world-model layer; outcome-logging node subscribes to slip/stuck/health topics; cloud sync via a robotics data service (Zenoh/MQTT store-and-forward).

**Performance.** Mostly offboard aggregation; onboard just reads a cached geo-layer — cheap. Watch storage growth; downsample/aggregate.

**Pitfalls.** Overfitting to stale experience (the field changed — tillage, new crop); alignment errors across passes (bad map-matching poisons the store); confounding (was it muddy, or was the robot heavier that day?) — log conditions richly.

**Open research.** Lifelong learning without catastrophic forgetting; transfer across fields/farms; causal attribution of failures; principled explore/exploit in safety-critical settings.

---

## C3 — Learned Traversability Estimation

**Why valuable.** Ag ground is a continuum (grass, mud, ruts, slopes, crop, ditches). Binary occupancy is wrong. Graded, semantic-, and robot-aware traversability directly reduces getting stuck, tipping, and crop damage — core reliability.

**Theory.** Traversability = a function from local terrain + robot state to a cost/risk of safe traversal: `T: (geometry, semantics, robot_state) → [0,1] risk + cost`. Learned from geometry (slope, roughness, step) + semantics (surface class) + *self-supervised outcomes* (did we slip/get stuck/vibrate?). Self-supervision is the key trick: the robot labels terrain by *how it actually drove over it* (IMU vibration, slip, motor current), producing free labels.

**Math.**
- Geometric features: slope `θ = atan(||∇h||)`, roughness = local height variance, step = max neighbor height diff.
- Risk model: `r = f_ϕ(features)`, learn `f_ϕ` by regression to observed outcome labels (slip ratio, vibration energy, current spikes) with uncertainty (deep ensembles / GP / evidential).
- Slip ratio `s = 1 - v_actual/v_commanded`; use as a self-supervised target.
- Traversal cost into planner: `c = w_r·r + w_e·energy + w_t·time`, uncertainty-inflated when confidence low.

**Algorithms.** CNN over BEV geometry+RGB → per-cell traversability; self-supervised label generation from proprioception; deep ensembles / evidential deep learning for uncertainty; GP regression for low-data regimes; classic geometric traversability (slope/step thresholds) as safe fallback and sanity bound.

**Software architecture.** A traversability node consuming elevation + semantics + (training-time) proprioceptive outcomes, producing a traversability layer of the world model, with uncertainty. A separate offline pipeline mines logs for self-supervised labels.

**Implementation strategy.** Phase 1: geometric traversability from `grid_map` (slope/roughness/step) — deterministic, safe, shippable. Phase 2: add semantic surface classes. Phase 3: self-supervised learned model refining geometry, validated to never be *less* conservative than the geometric bound in safety-critical cases.

**ROS 2 integration.** `grid_map`-based node; publishes `traversability` layer; feeds world model + a costmap plugin. Training pipeline offboard; model served via TensorRT.

**Performance.** Per-cell CNN on BEV is GPU-friendly; keep to local window; 10 Hz feasible on Orin. Geometric fallback is trivially cheap.

**Pitfalls.** Distribution shift across seasons/soils (retrain per condition); overconfident learned model driving into a bog — always bound by conservative geometry + uncertainty; label noise from bad slip estimation; negative obstacles (ditches, holes) are hard — sensor geometry matters.

**Open research.** Generalization across farms/soils; predicting *sinkage*/bogging before entry; combining terramechanics models with learning; long-range traversability from limited-range sensing.

---

## C4 — Prediction of Dynamic Agents

**Why valuable.** Safe, non-jerky behavior around workers, livestock, and machinery requires forecasting, not reacting. Also enables smoother, faster operation (don't stop for something that will clear).

**Theory.** Predict `p(future_trajectory | past, context, map)`. Futures are multimodal (a person may go left or right) — predict *distributions*, not points. Context = map/semantics + interactions between agents.

**Math.**
- Baselines: constant velocity/acceleration (Kalman forward roll-out).
- Learned: `p(Y|X) = Σ_k π_k · N(Y; μ_k, Σ_k)` (mixture over K modes), trained by NLL or via CVAE/diffusion.
- Metrics: minADE/minFDE over K samples, miss rate, NLL, and *calibration*.
- Occupancy-flow: predict future occupancy grid `O_{t+Δ}` + flow field, avoiding explicit agent enumeration (great for herds/flocks).

**Algorithms.** Constant-velocity + IMM (interacting multiple model) baselines; Social-LSTM/Trajectron++ (graph + CVAE); VectorNet/LaneGCN-style context encoding (adapt "lanes" → rows/paths); Transformer predictors; occupancy-flow nets. Start simple.

**Software architecture.** Prediction node subscribes to tracked objects (from world model) + map context; outputs predicted trajectories/occupancy with probabilities into the world-model dynamic layer; planner consumes predicted occupancy over the planning horizon.

**Implementation strategy.** Phase 1: constant-velocity + IMM for people/vehicles — surprisingly strong baseline, ship it. Phase 2: learned multimodal predictor for people; occupancy-flow for herds. Always keep the physics baseline as a safety floor.

**ROS 2 integration.** Consumes tracks; publishes predicted-occupancy grids stamped over horizon; planner (MPPI/MPC) reads them as time-varying costs.

**Performance.** Learned predictors are GPU; batch all agents; predict at ~5–10 Hz over 3–5 s horizon. Occupancy-flow is a fixed-cost grid regardless of agent count — good for crowds/herds.

**Pitfalls.** Overconfident single-mode predictions cause dangerous plans; poor calibration; ignoring the physics baseline; train/test domain gap (city-trained models fail on farm scenes); latency (a stale prediction is worse than none).

**Open research.** Joint (interaction-aware, scene-consistent) prediction; animal behavior models; long-tail rare maneuvers; tight prediction↔planning integration (game-theoretic, differentiable).

---

## C5 — Prediction-Aware / Uncertainty-Aware Planning (Trajectory layer)

**Why valuable.** Turns your existing MPPI into something far safer and smoother: plans that respect where agents *will be* and slow down when *unsure*.

**Theory.** Optimal control under uncertainty. MPPI is sampling-based stochastic optimal control: sample control sequences, roll out through dynamics, weight by cost, update. Make cost time-varying (from prediction) and risk-sensitive (from uncertainty).

**Math.**
- MPPI update: `u* = Σ_i w_i U_i`, `w_i ∝ exp(-1/λ · S(U_i))`, where `S` is trajectory cost (rollout through dynamics `x_{t+1}=f(x_t,u_t)`).
- Prediction-aware cost adds `Σ_t collision_cost(x_t, PredictedOccupancy_t)`.
- Risk-sensitive: optimize CVaR or mean+κ·std of cost; inflate obstacle radius by localization + prediction uncertainty.
- Chance constraints: `P(collision) ≤ δ` → inflate by `Φ^{-1}(1-δ)·σ`.

**Algorithms.** MPPI (you have it) → prediction-aware MPPI → risk-aware MPPI; alternatives: NMPC with chance constraints, contingency planning (plan a branch per predicted mode), CC-RRT for uncertainty.

**Software architecture.** Keep MPPI as the local controller; feed it (a) traversability cost, (b) time-varying predicted occupancy, (c) uncertainty-inflated obstacles, (d) experience cost. Dynamics model shared with control.

**Implementation strategy.** Incrementally enrich the MPPI cost: first traversability, then predicted occupancy, then uncertainty inflation, then risk measure. Each step is a measurable safety/comfort improvement.

**ROS 2 integration.** Nav2 supports MPPI controller — extend its cost via custom critics reading world-model layers. Or run a custom controller server.

**Performance.** MPPI is embarrassingly parallel → GPU; thousands of rollouts at 30–50 Hz on Orin. Time-varying occupancy queries must be O(1) grid lookups.

**Pitfalls.** Cost-term weight tuning hell (motivates *learned* costs, C6); myopia if horizon too short; sampling collapse; determinism for replay (seed control!); over-conservatism freezing the robot ("freezing robot problem").

**Open research.** Differentiable prediction+planning; learned samplers/proposals for MPPI; game-theoretic interaction; formal guarantees for sampling planners.

---

## C6 — Learning Costmaps / Learning to Plan

**Why valuable.** Hand-tuning cost weights is brittle and doesn't scale across fields/conditions. Learning cost from expert demos and outcomes yields behavior that matches operator intent and generalizes.

**Theory.** Inverse Reinforcement Learning / Inverse Optimal Control: recover the cost function that makes expert demonstrations optimal. Then plan with the learned cost. Alternative: imitation learning of the policy directly (with a safety filter).

**Math.**
- Max-Entropy IRL: `p(τ) ∝ exp(-C_θ(τ))`; maximize demo likelihood, gradient matches expected vs demo feature counts.
- Deep IRL: `C_θ` a neural net over map/context features.
- Imitation (BC): minimize `E[ℓ(π_θ(s), a_expert)]`; beware distribution shift (DAgger fixes).

**Algorithms.** MaxEnt deep IRL; learning cost volumes for search planners; end-to-end differentiable planners (value-iteration nets, differentiable A*); imitation + DAgger; offline RL from logged outcomes.

**Software architecture.** Offline: mine (demo, context) pairs from operator-driven logs → train cost model. Online: cost model outputs a cost layer to the planner; safety core bounds it.

**Implementation strategy.** Phase 1: learn *weights* of hand-designed cost terms from demos (low-risk). Phase 2: learn a cost *residual* over features. Phase 3: learned cost volume for the global planner. Never let learned cost bypass the safety core.

**ROS 2 integration.** Learned cost as a world-model/costmap layer; training offboard; served via ONNX/TensorRT.

**Performance.** Inference cheap (a small CNN over BEV); training offboard. 

**Pitfalls.** Demonstrations encode operator quirks and biases; distribution shift; reward hacking in RL; unsafe extrapolation — keep the safety envelope; hard to debug "why did it cost that?" — invest in visualization.

**Open research.** Sample-efficient IRL; safe offline RL; interpretable learned costs; combining learned cost with hard constraints and guarantees.

---

## C7 — Robust & Self-Healing Localization

**Why valuable.** Localization failure is the #1 cause of field interventions. Self-healing (detect degradation, reconfigure automatically, relocalize) is the difference between "call the operator" and "keep working."

**Theory.** Multi-sensor fusion with **integrity monitoring**: continuously test whether each sensor's measurements are consistent with the estimate; detect and exclude faults (RAIM-style, from aviation GNSS); reconfigure the estimator; trigger relocalization when lost. State estimation on manifolds; robust back-ends.

**Math.**
- ESKF fusion of GNSS/IMU/odom; state on SE(3), error-state in the tangent space.
- Innovation test: `γ = ν^T S^{-1} ν ~ χ²`; if `γ > threshold`, measurement is an outlier → reject/down-weight.
- Factor-graph smoothing (iSAM2): MAP over a window; switchable constraints / dynamic covariance scaling for robustness.
- Integrity: protection levels (bound on position error at given integrity risk), consistency (NEES/NIS tests).

**Algorithms.** `robot_localization`/EKF → tightly-coupled ESKF → factor-graph (GTSAM) smoothing; LiDAR-inertial odometry (FAST-LIO2, LIO-SAM, KISS-ICP) as GNSS-denied backup; scan-matching relocalization; RAIM/FDE for GNSS fault detection; place recognition (Scan Context, learned descriptors) for kidnapped-robot recovery.

**Software architecture.** A fusion core + a **health/integrity monitor** that watches innovations, GNSS quality, slip, and covariance, and a **supervisor** that switches modes (full fusion → LiDAR-odom → stop-and-relocalize) via a state machine. Expose a single "localization integrity" signal to behavior planning.

**Implementation strategy.** Phase 1: solid ESKF fusion + covariance/NIS monitoring + a "localization confidence" topic. Phase 2: automatic GNSS fault exclusion + LiDAR-odom fallback. Phase 3: automatic relocalization from place recognition; map-relative localization against field maps.

**ROS 2 integration.** Replace/augment `robot_localization`; publish `/localization/health`; behavior tree reacts to low integrity (slow, stop, relocalize, escalate). Use `/tf` discipline.

**Performance.** ESKF is cheap; factor-graph smoothing bounded by window size; LiDAR-odom is the heavy part (GPU/opt). Must stay real-time (localization can't lag).

**Pitfalls.** Covariance lies (overconfident filters); wheel slip silently corrupting odom; GNSS multipath near structures/canopy; frame/extrinsic calibration errors; relocalization aliasing in self-similar rows (use GNSS prior to disambiguate).

**Open research.** Learned integrity monitoring; robust place recognition under seasonal change; guaranteed-integrity localization for safety cases; long-term map maintenance.

---

## C8 — Semantic & Human/Animal-Aware Navigation

**Why valuable.** Behavior driven by *meaning* (crop rows, keep-out zones, people, livestock) is safer, more acceptable, and unlocks tasks geometry alone can't (row-following, zone rules, socially-aware yielding).

**Theory.** Semantic navigation = planning over a representation annotated with categories + rules; human-aware navigation adds social/comfort models (proxemics) and prediction-coupled cost. Constraints and preferences are expressed semantically, compiled into costs/rules.

**Math.**
- Semantic cost: `c(cell) = Σ_k w_k · 1[class_k]` + rule penalties (keep-out = ∞ inside zone).
- Proxemics: cost that grows near humans, e.g. asymmetric Gaussian around predicted person pose; `c_social = A·exp(-((Δ)^T Σ^{-1}(Δ))/2)`.
- Rule layer: a declarative policy (temporal logic / rules) compiled to constraints: e.g., LTL specs for "always keep out of zone Z," "eventually cover all rows."

**Algorithms.** Semantic segmentation → semantic map; rule/temporal-logic checking; social-force / prediction-aware costs; formal task specs (LTL/STL) for behavior guarantees.

**Software architecture.** Semantic overlay in world model + a **rules/constraints service** (declarative farm rules: zones, speed limits near people, crop no-crush) that behavior + trajectory planners query. Human-aware costs come from prediction (C4).

**Implementation strategy.** Phase 1: static semantic zones (geofenced keep-outs, headland-only, speed zones) from the field map — huge safety value, low complexity. Phase 2: dynamic human-aware costs. Phase 3: declarative rule engine + verification.

**ROS 2 integration.** Semantic/zone layers as costmap/world-model layers; behavior tree nodes for "slow near human," "yield," "stop for animal"; rules loaded from cloud field config.

**Performance.** Zone checks trivial; social costs are per-agent Gaussians — cheap; semantic seg is the GPU cost (already in perception).

**Pitfalls.** Misclassification with real consequences (scarecrow vs child — bias conservative); proxemics tuning; over-stopping around workers (annoying, unproductive); rule conflicts (need priority resolution).

**Open research.** Open-vocabulary semantics; formal guarantees with learned perception; culturally/context-appropriate social navigation; verification of neuro-symbolic policies.

---

## C9 — Navigation Health Monitoring & Graceful Degradation

**Why valuable.** Detecting "autonomy is degrading" *before* failure lets you slow, reroute, or escalate — converting hard failures (intervention, damage) into soft ones (a brief slowdown). Directly improves the intervention-rate KPI that governs unit economics.

**Theory.** Runtime verification + anomaly detection over the autonomy stack's internal signals. Model "healthy" behavior; detect deviation; map health → behavior (Simplex/runtime-assurance).

**Math.**
- Health features: localization covariance trace, planner cost/feasibility, perception confidence, prediction error, control tracking error, comms latency.
- Anomaly score: Mahalanobis distance to healthy distribution, or a learned OOD/one-class model; CUSUM for drift detection.
- Health → speed limit mapping (monotone): more anomaly ⇒ lower allowed speed ⇒ safe-stop.

**Algorithms.** Statistical process control (CUSUM, EWMA); one-class SVM / autoencoders / deep ensembles for OOD; runtime monitors (STL specs checked online); conformal prediction for calibrated confidence.

**Software architecture.** A **health aggregator** subscribing to per-module health signals, computing a global autonomy-health state, feeding the behavior layer and the safety core, and triggering data-engine event uploads.

**Implementation strategy.** Phase 1: define + publish per-module health signals (this alone is transformative for debugging). Phase 2: aggregate into a health state + graceful-degradation policy. Phase 3: learned OOD detection + predictive degradation.

**ROS 2 integration.** `diagnostics`-style health topics; a health-manager node; behavior tree consumes health; auto-trigger MCAP event clips on anomalies.

**Performance.** Cheap (scalar signals); the value is architectural discipline, not compute.

**Pitfalls.** Alert fatigue (too sensitive); miscalibrated confidence; monitoring adds coupling — keep it read-only; garbage-in if modules don't report honestly.

**Open research.** Calibrated uncertainty for deep perception; predictive failure models; formal runtime assurance with learned components.

---

## C10 — Fleet Intelligence & Multi-Robot Coordination

**Why valuable.** Fleet-wide learning (every robot benefits from every robot's experience) and coordination (coverage, deconfliction, shared resources) are how you scale economically (Amazon lesson).

**Theory.** Distributed estimation + multi-agent planning + federated/centralized learning. Map merging (align + fuse per-robot maps); task allocation (assignment/optimization); deconfliction (priority/reservation or optimization); fleet learning (aggregate rare events).

**Math.**
- Map merging: estimate relative transforms `T_{ij}∈SE(3)` via overlap/GNSS; pose-graph fusion.
- Task allocation: assignment/ILP minimizing makespan or cost; auction algorithms for decentralization.
- Coverage: decompose field into cells; solve coverage/TSP-like ordering per robot with balance.
- Deconfliction: space-time reservation (prioritized planning) or CBS (conflict-based search) for multi-agent path finding.

**Algorithms.** Map merging (GNSS-aided pose-graph); Hungarian/auction task allocation; CBS/prioritized planning for MAPF; boustrophedon coverage decomposition; federated learning for models; cloud aggregation for experience/maps.

**Software architecture.** Cloud **fleet manager** (assignment, scheduling, shared map/experience service) + on-robot **fleet client** (reports state, receives tasks, coordinates locally with neighbors over Zenoh). Shared world-model/experience artifacts versioned centrally.

**Implementation strategy.** Phase 1: shared field maps + fleet-wide experience aggregation (async, cloud). Phase 2: centralized task allocation + coverage splitting. Phase 3: real-time deconfliction at shared resources (gates, roads, chargers). Multi-robot MAPF only where robots actually interact.

**ROS 2 integration.** Zenoh for robot↔cloud and robot↔robot (WAN/lossy-friendly); VDA5050-inspired fleet interface; per-robot namespaces; cloud services over gRPC/REST.

**Performance.** Coordination is mostly cloud/async; on-robot local deconfliction must be fast but only near conflicts. Bandwidth-aware sync is the real constraint (rural connectivity).

**Pitfalls.** Connectivity assumptions (design for disconnection — robots must be safe & useful offline); map-merge misalignment; centralized bottlenecks/SPOFs; clock sync across robots.

**Open research.** Robust decentralized coordination under comms loss; federated learning for robotics at scale; lifelong shared maps; guaranteed-safe multi-robot interaction.

---

## C11 — AI Copilots, Autonomous Diagnostics, Mission Replay, Foundation Models

Grouped because they share infra (logging, cloud, ML serving) and are mostly year 3–5.

**AI copilot for operators.** *Why:* one operator supervises many robots; a VLM/LLM assistant explains "what am I looking at / why did the robot stop / what should I do," turning raw telemetry into decisions. *Theory/algorithms:* VLMs over camera + world-model state; RAG over manuals/logs; tool-use agents that query telemetry. *Arch:* cloud service with access to live world model + logs + docs; strictly advisory (never commands the safety core). *Pitfalls:* hallucination — ground in retrieved facts, keep human authority, never in the safety path.

**Autonomous diagnostics & predictive maintenance.** *Why:* field downtime is expensive; predict failures (bearings, motors, sensors) before they strand a robot. *Theory/math:* anomaly detection + remaining-useful-life estimation from vibration/current/temperature time-series; survival models; `RUL` regression. *Algorithms:* spectral features + gradient-boosted / deep time-series models; changepoint detection. *Arch:* on-robot feature extraction → cloud RUL models → maintenance scheduling. *Pitfalls:* few failure examples (use physics + simulation + fleet aggregation).

**Mission replay.** *Why:* debug, validate, and *train* from real missions; the substrate for the data engine and CI. *Theory:* deterministic record/replay — same inputs ⇒ same outputs. *Algorithms/arch:* MCAP logging of all inputs + decisions; a replay runner that re-injects logged messages into unchanged nodes; interactive visualization (Foxglove/rerun) with world-model + decision overlays; log-driven CI gating merges on golden/failure logs. *Pitfalls:* nondeterminism (threads, time, RNG, wall-clock I/O) — engineer determinism deliberately; log completeness (missing an input breaks replay).

**Foundation models for robotics.** *Why (the bet):* open-vocabulary perception ("is that a child, a deer, or a scarecrow?") and generalist behavior across tasks/platforms could collapse long-tail engineering. *Theory/algorithms:* VLMs (open-vocab detection/segmentation), VLA (vision-language-action) policies, world-model foundation models. *Arch:* big offboard models for auto-labeling + open-vocab queries; distilled small models onboard. *Pitfalls:* latency, cost, hallucination, and safety — keep foundation models offboard or advisory for now; use them to *label and understand*, not to *drive*, until evidence says otherwise. This is a year 4–5 exploration with a clear "graduate to production only when validated" gate.

---

## Cross-cutting: how these compose

- **World model (C1)** is written by perception + **traversability (C3)** + **localization (C7)** + **prediction (C4)**, enriched by **semantics (C8)** and **experience (C2)**.
- **Planning (C5, C6)** reads the world model; **health monitoring (C9)** watches everything; **safety core** bounds everything.
- **Fleet (C10)** and the **data engine / replay / copilots / diagnostics (C11)** close the loop over the whole fleet across seasons.

Build the spine (C1) and the loop (C11 replay + data engine) first; everything else plugs into them.

Next: `05-flagship-projects.md` — how to sequence all this into shippable projects.
