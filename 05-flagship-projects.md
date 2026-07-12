# 05 — Flagship Projects (Ambitious but Practical, Sequenced)

This is your execution backlog: concrete projects, sequenced across ~3–5 years, each with a crisp goal, why-now, dependencies, deliverable, and a definition of done. Projects map to capabilities in `04` (C1–C11).

**Sequencing philosophy:** build the *spine* and the *loop* before the *intelligence*. You cannot safely deploy learned components without record/replay, sim, and a safety core already in place. Resist the temptation to start with the sexy ML.

Each project has a **"MVP in weeks / full in quarters"** framing so you always ship something small and real.

---

## PHASE 0 — Foundations (Months 0–9). "Make Nav2 observable, safe, and reproducible."

### P0.1 — Record / Replay / Log-driven CI (C11)
- **Why now:** nothing else is safe or fast without it.
- **MVP (weeks):** MCAP logging of all sensor + decision topics; a replay script that re-runs a node graph on a log deterministically.
- **Full (quarter):** golden-log regression suite in CI; every PR replays against ~20 curated field logs; metrics (path length, min-obstacle-distance, interventions) gate merges. Foxglove/rerun visualization of world model + decisions.
- **Done when:** you can reproduce a specific field failure bit-for-bit on a laptop and in CI.

### P0.2 — Independent Safety Core + explicit ODD (Safety layer)
- **Why now:** license to deploy; incident defense.
- **MVP:** a separate process/MCU enforcing geofence, velocity/curvature/slope envelopes, min-distance stop, e-stop, watchdog heartbeats; independent of the ROS planning stack.
- **Full:** written ODD document; hazard analysis (HARA-lite); Simplex fallback controller (safe-stop trajectory) triggered by monitors; wire toward ISO 25119/18497 concepts.
- **Done when:** any single ROS node crash or bad plan results in a safe stop, provably, without operator action.

### P0.3 — Simulation + Digital Twin baseline (Sim layer)
- **Why now:** validate before field; generate long-tail data.
- **MVP:** Gazebo or Isaac Sim model of one robot + one field; run the *exact* autonomy stack in sim.
- **Full:** replay-driven sim (real logged sensors → new software); procedural field generation; sim in CI. Photoreal sensor sim (Isaac) if perception ML is near.
- **Done when:** you routinely test new nav logic in sim before touching a real robot, and re-simulate every field incident.

### P0.4 — Health signals + telemetry backbone (C9, Monitoring)
- **MVP:** every module publishes structured health (localization covariance, planner feasibility, perception confidence, comms); a health aggregator + Grafana dashboard.
- **Full:** interesting-event triggers that auto-upload MCAP clips (disengagement, near-miss, high uncertainty, novel object).
- **Done when:** you can see fleet health at a glance and the fleet auto-collects its own hard cases.

**Phase 0 exit criteria:** you have a *data engine skeleton* (log → trigger → upload → replay → sim → CI) and a *safety core*. Now you can safely add intelligence.

---

## PHASE 1 — The Spine (Months 6–18). "Replace the costmap with a world model; exploit repeat visits."

### P1.1 — Persistent Semantic Temporal World Model (C1) ★ flagship
- **Why now:** everything else builds on it.
- **MVP:** `grid_map`-based store with temporal persistence + elevation + occupancy; a Nav2 costmap plugin that renders it (so existing planners keep working). Fixes the "forgets obstacles / oscillates" bug immediately.
- **Full:** semantic overlay (surface/crop/person classes), dynamic-object layer with tracking, uncertainty, clean query API; BEV fusion variant on GPU.
- **Done when:** planners consume the world model via a stable versioned API and you can swap the costmap out.

### P1.2 — Geometric → Learned Traversability (C3)
- **MVP:** deterministic slope/roughness/step traversability from elevation map → cost layer. Ship it; it alone reduces stuck/tip events.
- **Full:** self-supervised learned traversability (labels from IMU vibration / slip / motor current), uncertainty-aware, bounded by the geometric safe layer.
- **Done when:** measurable drop in stuck/tip incidents vs geometric baseline in sim + field.

### P1.3 — Experience-Based Field Memory (C2) ★ flagship (ag moat)
- **MVP:** geo-tag outcomes (stuck, slip, timing, energy); render a per-field "trouble heatmap."
- **Full:** experience cost layer fed to the planner, conditioned on season/moisture/payload; fleet aggregation.
- **Done when:** the robot demonstrably avoids historically-troublesome areas and improves route choice over repeated passes.

### P1.4 — Robust Localization + confidence (C7, phase 1)
- **MVP:** tightly-coupled GNSS/IMU/odom ESKF (or GTSAM) + NIS/covariance monitoring + `/localization/health`.
- **Full:** GNSS fault exclusion + LiDAR-odometry fallback.
- **Done when:** localization degradation is detected and reported, and behavior reacts (slows/stops) rather than silently drifting.

**Phase 1 exit criteria:** a semantic, temporal world model + traversability + field memory + honest localization confidence, all replacing the flat costmap — with everything replayable and safe.

---

## PHASE 2 — Intelligence Layer (Months 15–30). "Understand and predict; plan smartly."

### P2.1 — Dynamic-agent Prediction (C4)
- **MVP:** constant-velocity + IMM prediction for tracked people/vehicles into the world model.
- **Full:** learned multimodal predictor for people; occupancy-flow for herds/flocks.
- **Done when:** planner uses time-varying predicted occupancy; smoother, safer behavior near people/animals (measured by min-distance + jerk + intervention rate).

### P2.2 — Prediction-Aware & Uncertainty-Aware MPPI (C5)
- **MVP:** extend MPPI cost with traversability + predicted occupancy + uncertainty inflation (custom Nav2 MPPI critics).
- **Full:** risk-sensitive (CVaR) cost; contingency branches per predicted mode.
- **Done when:** the robot slows when unsure and routes around predicted futures, without freezing.

### P2.3 — Semantic & Human-Aware Navigation (C8)
- **MVP:** static semantic zones from the field map (keep-outs, headland-only, speed zones) + "stop for person/animal" behaviors.
- **Full:** proxemics-based human-aware costs; declarative farm-rule engine (zones, speeds, no-crush) with priority resolution.
- **Done when:** operators can define farm rules that the robot provably respects.

### P2.4 — Self-Healing Localization (C7, phase 2)
- **Full:** automatic relocalization (place recognition), map-relative localization against field maps, mode-switching supervisor.
- **Done when:** the robot recovers from GNSS loss / kidnapping without operator intervention in the common cases.

### P2.5 — Learning Costmaps (C6)
- **MVP:** learn weights of existing cost terms from operator demonstrations.
- **Full:** learned cost residual / cost volume, safety-bounded.
- **Done when:** learned cost matches operator intent better than hand-tuned, validated in replay.

**Phase 2 exit criteria:** the robot understands *what* is around it, predicts *what will happen*, plans with *risk awareness*, and recovers from localization trouble on its own.

---

## PHASE 3 — Fleet & The Loop Closes (Months 27–42). "One brain across the fleet."

### P3.1 — Continuous-Learning Pipeline in production (C11, Continuous learning)
- Active-learning triggers → auto-label (multi-pass 4D field reconstruction) → train → sim+replay validation gates → shadow mode → OTA. **Measure loop cycle time as a KPI.**
- **Done when:** a field failure can become a validated, deployed model improvement in days, not months.

### P3.2 — Fleet Intelligence: shared maps + fleet learning (C10)
- Cloud map + experience service; every robot's experience improves every robot; change detection on field maps.
- **Done when:** a hazard discovered by one robot is avoided by all robots on the next pass.

### P3.3 — Multi-Robot Coordination (C10)
- Task allocation + coverage splitting; deconfliction at shared resources (gates, roads, chargers); local space-time reservation.
- **Done when:** N robots cover a farm faster than N independent robots, without conflicts, and stay safe when comms drop.

### P3.4 — Navigation Health Monitoring + Graceful Degradation (C9)
- Aggregated autonomy-health → speed/behavior policy → escalation. Learned OOD detection.
- **Done when:** hard failures convert to soft failures (slowdown/escalation) measurably.

### P3.5 — AI Copilot for Operators (C11)
- VLM/LLM assistant grounded in live world model + logs + manuals; explains stops, suggests actions; one operator supervises many robots. Strictly advisory.
- **Done when:** operator-to-robot supervision ratio improves with maintained safety.

**Phase 3 exit criteria:** the fleet learns as one system, coordinates, degrades gracefully, and is supervised efficiently by humans.

---

## PHASE 4 — Platform & Frontier (Months 39–60). "A platform, and selective frontier bets."

### P4.1 — Autonomous Diagnostics + Predictive Maintenance (C11)
- RUL models from vibration/current/thermal; maintenance scheduling; fleet-aggregated failure learning.
- **Done when:** predicted-and-prevented failures exceed field-stranding failures.

### P4.2 — Foundation-Model Perception (frontier, C11)
- Offboard VLMs for open-vocabulary understanding + auto-labeling; distilled small onboard models. Advisory/labeling only until validated.
- **Done when:** novel-object handling and labeling throughput measurably improve, with no safety-path dependence.

### P4.3 — (Partly) Learned World Models / Predictive Planning (frontier, C1/C5)
- Neural/latent world model for prediction & planning research; predictive planning against forecast futures (crop growth, weather).
- **Done when:** a validated, bounded win over the modular baseline in specific scenarios — or a clear, documented "not yet" decision.

### P4.4 — The Platform (productization)
- Stable SDK/APIs (world model, missions, maps, fleet) so new ag tasks/products (spraying, scouting, harvesting-assist) build on your autonomy without touching the core. Agronomic analytics as a second product.
- **Done when:** a new capability ships as an app on the platform, not a fork of the stack.

---

## The one-page sequencing rule

> **Loop & Safety (P0) → Spine (P1) → Intelligence (P2) → Fleet (P3) → Platform & Frontier (P4).**
> Never add a learned component before you can replay it, simulate it, and safely bound it. Always ship a deterministic MVP before its learned upgrade.

## Portfolio balancing (as a leader)

At any time run a mix: ~60% reliability/ops (make the current thing work in more fields), ~30% differentiators (the spine/intelligence moat), ~10% frontier bets (learn early, adopt late). Adjust with commercial pressure, but never let frontier bets starve reliability — reliability is what customers actually pay for.

Next: `06-resources.md`.
