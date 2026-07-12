# 06 — Curated Learning Resources

Opinionated and filtered. I list the *industry-standard* and *academically-respected* resources per topic, and mark each:
**[F]** foundational (do this) · **[R]** reference (dip in as needed) · **[A]** advanced/frontier.

Don't try to consume it all — `07` and `09` tell you how to sequence and pace. Titles/authors are given so you can find current editions and official pages yourself; verify links, since URLs and course numbers change year to year.

---

## Mathematics (the bedrock)
- **[F]** *Mathematics for Machine Learning* — Deisenroth, Faisal, Ong (free PDF). The efficient bridge from rusty math to ML-ready.
- **[F]** *Linear Algebra* — Gilbert Strang (MIT 18.06 lectures on OCW/YouTube). The canonical linear algebra course.
- **[R]** *Probability Theory: The Logic of Science* — Jaynes (deep Bayesian intuition; read selectively).
- **[F]** 3Blue1Brown (YouTube): *Essence of Linear Algebra*, *Essence of Calculus*. Best intuition-builders in existence — watch before/with the rigorous texts.
- **[R]** *Convex Optimization* — Boyd & Vandenberghe (free PDF + Stanford EE364A videos). Essential for MPC/estimation.
- **[R]** *An Introduction to Optimization* / Nocedal & Wright *Numerical Optimization* [A] for the serious optimization backbone.
- **[F]** *State Estimation for Robotics* — Timothy Barfoot (free PDF). The best single text on SE(3)/SO(3), matrix Lie groups, and estimation on manifolds — directly relevant to localization.

## Robotics foundations
- **[F]** *Probabilistic Robotics* — Thrun, Burgard, Fox. The bible for localization, mapping, filters. Non-negotiable.
- **[F]** *Modern Robotics* — Lynch & Park (free book + Coursera specialization + YouTube). Kinematics/dynamics/control with clean math.
- **[R]** *Planning Algorithms* — Steven LaValle (free online). The reference for motion planning.
- **[R]** *Principles of Robot Motion* — Choset et al. (planning, sensing).
- **[F]** *Introduction to Autonomous Mobile Robots* — Siegwart, Nourbakhsh, Scaramuzza. Excellent mobile-robot systems overview.
- **[F] Course:** University of Bonn — Cyrill Stachniss's *Mobile Sensing and Robotics* / *SLAM* / *Photogrammetry* lectures (YouTube). Outstanding, free, rigorous, practical. Arguably the best free robotics-perception lectures online.

## Control theory
- **[F]** *Feedback Systems* — Åström & Murray (free PDF). The clearest intro to control for engineers.
- **[R]** *Predictive Control for Linear and Hybrid Systems* — Borrelli, Bemporad, Morari (MPC bible).
- **[A]** *Model Predictive Control: Theory, Computation, and Design* — Rawlings, Mayne, Diehl.
- **[F]** Steve Brunton (YouTube): *Control Bootcamp*, *Data-Driven Science & Engineering*. Superb intuition; watch alongside the books.
- **[R]** *Optimal Control* material — Underactuated Robotics (Russ Tedrake, MIT 6.832, free videos + notes) — brilliant for trajectory optimization, LQR, and robot control.

## Estimation, SLAM, localization
- **[F]** Barfoot *State Estimation for Robotics* (above).
- **[F]** Stachniss SLAM lectures (above).
- **[R]** *Factor Graphs for Robot Perception* — Dellaert & Kaess (foundations behind GTSAM/iSAM2).
- **[R]** Papers: LIO-SAM, FAST-LIO2, KISS-ICP, ORB-SLAM3, VINS-Fusion, Scan Context. Read the papers *and* the code.
- **[R]** GNSS/RTK: any solid GNSS textbook (e.g., *Understanding GPS/GNSS* — Kaplan & Hegarty) + RAIM/integrity monitoring literature.

## Perception & computer vision
- **[F]** *Multiple View Geometry in Computer Vision* — Hartley & Zisserman [R] (the geometry reference).
- **[F] Course:** Stanford CS231n (CNNs for visual recognition — notes + lectures).
- **[F]** *Deep Learning* — Goodfellow, Bengio, Courville (free HTML). The theory reference.
- **[F]** fast.ai *Practical Deep Learning* (free) — best practical on-ramp if DL is new.
- **[R]** BEV/occupancy & 3D detection papers: Lift-Splat-Shoot, BEVFusion, BEVFormer, and the occupancy-network line. nuScenes / Waymo Open Dataset papers.
- **[R]** Segmentation/detection: point cloud (PointNet/PointNet++, VoxelNet, PointPillars), 2D (Mask R-CNN, DETR), open-vocab (SAM, Grounding-DINO, CLIP).

## Planning (mission → trajectory)
- **[F]** LaValle *Planning Algorithms* (above).
- **[R]** MPPI: Williams et al. *Information-Theoretic MPC / MPPI* papers.
- **[R]** Search & lattice: ARA*/AD*/D* Lite (Likhachev, Stentz, Koenig); Experience Graphs (Phillips, Likhachev).
- **[R]** Coverage path planning surveys (boustrophedon, cellular decomposition) — directly relevant to ag.
- **[R]** Multi-robot: CBS (Sharon et al.), survey of MAPF (Stern et al.).
- **[R]** Nav2 documentation + papers (Macenski et al., *The Marathon 2* / Nav2 papers) — know your current stack's design intent cold.

## Prediction & learning for driving/robotics
- **[R]** Trajectory prediction: Social-LSTM, Trajectron++, VectorNet, LaneGCN, and occupancy-flow papers.
- **[R]** Waymo Open Motion Dataset + Sim Agents challenge papers (state of the art in prediction/sim).
- **[R]** *Reinforcement Learning: An Introduction* — Sutton & Barto (free PDF) [F for RL].
- **[A]** Offline RL surveys (Levine et al.); IRL (Ziebart MaxEnt IRL; Ng & Russell).
- **[A]** World models: Ha & Schmidhuber *World Models*; Dreamer (Hafner et al.); occupancy-flow.

## Machine-learning systems / MLOps for robotics
- **[F]** *Designing Machine Learning Systems* — Chip Huyen. Best practical MLOps text.
- **[R]** *Machine Learning Design Patterns* — Lakshmanan et al.
- **[R]** Data/versioning: DVC, lakeFS, MCAP/rosbag2 docs. Model serving: TensorRT, ONNX Runtime, Triton docs.
- **[R]** Tesla AI Day talks (2021/2022, YouTube) — the clearest public window into a production data engine + auto-labeling. Watch critically.

## ROS 2, middleware, real-time
- **[F]** Official ROS 2 documentation (docs.ros.org) — concepts, QoS, executors, lifecycle, composition, DDS.
- **[F]** Nav2 documentation (docs.nav2.org) + the Nav2 GitHub. Read the source of the parts you're extending.
- **[R]** *Programming Robots with ROS* (older, ROS 1, still conceptually useful) → prefer official ROS 2 tutorials + community (Articulated Robotics YouTube by Josh Newans — excellent practical ROS 2).
- **[R]** DDS/QoS deep material; Cyclone DDS + Zenoh docs. `PREEMPT_RT` and real-time Linux resources.

## Simulation & digital twins
- **[F]** NVIDIA Isaac Sim / Isaac ROS / Isaac Lab docs + tutorials. Gazebo (Harmonic/Ionic) docs.
- **[R]** Domain randomization papers (Tobin et al.); sim-to-real surveys.
- **[R]** CARLA (autonomous driving sim) docs/papers — patterns transfer even if you don't use it directly.

## Safety & functional safety
- **[F]** ISO 25119 (ag machinery functional safety) and ISO 18497 (ag autonomy) — read summaries first, then standards.
- **[F]** ISO 26262 (automotive functional safety) + ISO 21448 SOTIF — learn the *mental models* (ASIL, HARA, safety case, safety of the intended function). These shape how you architect ML safely.
- **[R]** *Engineering a Safer World* — Nancy Leveson (STPA, systems safety thinking; free PDF). Genuinely changes how you think about failure.
- **[R]** Runtime assurance / Simplex architecture papers (Sha et al.).

## GPU / high-performance C++ / embedded
- **[F]** *Effective Modern C++* — Scott Meyers; *A Tour of C++* — Stroustrup. Then *C++ Concurrency in Action* — Williams.
- **[R]** CppCon talks (YouTube) — performance, concurrency, real-time C++.
- **[R]** *Programming Massively Parallel Processors* — Kirk & Hwu (CUDA). NVIDIA CUDA docs + Nsight.
- **[R]** *Computer Systems: A Programmer's Perspective* — Bryant & O'Hallaron (systems fundamentals).

## Distributed systems & cloud
- **[F]** *Designing Data-Intensive Applications* — Martin Kleppmann. The best systems book of the last decade; directly relevant to fleet/cloud/data platform.
- **[R]** *Site Reliability Engineering* — Google (free online). Ops mindset for running robots as a fleet.
- **[R]** Kubernetes docs; a stream-processing intro (Kafka/Flink concepts).

## Systems engineering, leadership, product
- **[F]** *The Manager's Path* — Camille Fournier (engineering leadership arc).
- **[F]** *An Elegant Puzzle* — Will Larson (scaling eng orgs/systems).
- **[R]** *Staff Engineer* — Will Larson (the technical-leadership track you're on).
- **[R]** *Team Topologies* — Skelton & Pais (org design for platforms).
- **[R]** *Inspired* — Marty Cagan (product management for tech products).
- **[R]** *Thinking in Systems* — Donella Meadows (systems thinking, short and superb).
- **[R]** *The Design of Everyday Things* — Norman (operator UX matters in autonomy).

## Research skills
- **[F]** "How to Read a Paper" — Keshav (3-pass method; short, do it this week).
- **[R]** Papers With Code, arXiv-sanity, and following key labs/venues: CoRL, RSS, ICRA, IROS, CVPR, NeurIPS, ICLR. Waymo/Wayve/NVIDIA research blogs.
- **[R]** Andrej Karpathy (YouTube/blog) — neural nets from scratch; superb for building deep intuition.

## Ag-robotics specific
- **[R]** *Precision Agriculture* literature; journals: *Journal of Field Robotics*, *Computers and Electronics in Agriculture*, *Biosystems Engineering*.
- **[R]** Datasets: Sugar Beets / BonnBeetClouds (Bonn), agri-robotics datasets, RELLIS-3D and RUGD (off-road traversability), CADC/Boreas (adverse conditions).
- **[R]** Off-road autonomy: DARPA-era off-road papers; recent self-supervised traversability work (e.g., BADGR, WayFAST, and the off-road learning line).
- **[R]** Groups to follow: University of Bonn (Stachniss / ag robotics), CMU Field Robotics Center, ETH RSL (legged/terrain, control), Oxford Robotics Institute, Blue River / John Deere publications.

## YouTube channels (worth subscribing)
- Cyrill Stachniss (robotics/SLAM lectures) · Steve Brunton (control/dynamics/ML) · 3Blue1Brown (math) · Articulated Robotics (practical ROS 2) · Andrej Karpathy (deep learning) · Two Minute Papers (research awareness, low depth) · MIT OCW (Tedrake Underactuated Robotics).

## Blogs / newsletters
- Nav2 / Open Robotics blog · NVIDIA robotics/dev blogs · Wayve, Waymo, and comma.ai engineering posts (for AV thinking) · The Batch (Andrew Ng) · Import AI (Jack Clark) for AI landscape awareness.

**How to use this list:** in `07`, each week points to the *specific* subset here. Never open more than 1–2 primary resources per week. Depth over breadth.

Next: `07-52-week-study-plan.md`.
