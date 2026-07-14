# 11 — Annotated Reference Library (Repos, Datasets, Courses, Papers)

The "existing solutions to build on" catalogue. Complements `06-resources.md` (which is books/courses for *learning*); this one is code/datasets/papers for *building*. Links were verified as real at time of writing — **always check each repo's README for the branch matching your ROS 2 distro**, since branches and APIs change. Where a project is ROS 1-only or research-grade, it's flagged.

Compliance note: descriptions are paraphrased/summarized from the projects' own materials.

---

## A. Middleware, logging, tooling, visualization
| Project | Link | Use it for |
|---|---|---|
| ROS 2 (docs) | https://docs.ros.org/ | The platform. Read QoS, executors, lifecycle, composition. |
| Nav2 (docs) | https://docs.nav2.org/ · https://github.com/ros-navigation/navigation2 | Your current stack; extend its plugins/critics. |
| rmw_zenoh | https://github.com/ros2/rmw_zenoh | Robot↔cloud / multi-robot transport over lossy/WAN links (Tier-1 in ROS 2 Kilted). |
| Cyclone DDS | https://github.com/eclipse-cyclonedds/cyclonedds | Predictable on-robot DDS. |
| MCAP | https://github.com/foxglove/mcap | Log format (ROS 2 default). Readers in C++/Py/Go/Rust/TS. |
| rosbag2 | https://github.com/ros2/rosbag2 | Record/replay; MCAP storage plugin. |
| Foxglove | https://foxglove.dev/ | Log + live visualization, remote debugging, layouts. |
| rerun | https://github.com/rerun-io/rerun | Temporal/ML-friendly visualization (great for perception debugging). |
| PlotJuggler | https://github.com/facontidavide/PlotJuggler | Time-series introspection of bags/topics. |
| diagnostics | https://github.com/ros/diagnostics | Health/telemetry backbone. |

## B. Localization, odometry, SLAM, state estimation

The complete JABAS planar localization architecture and execution plan is in [`12-planar-agricultural-localization-design.md`](12-planar-agricultural-localization-design.md).

| Project | Link | Use it for | Notes |
|---|---|---|---|
| robot_localization | https://github.com/cra-ros-pkg/robot_localization | EKF/UKF GNSS+IMU+odom fusion | Start here for P1.4. |
| GTSAM | https://github.com/borglab/gtsam | Factor-graph smoothing (iSAM2), tight fusion, integrity | Graduate target for the fusion core. |
| KISS-ICP | https://github.com/PRBonn/kiss-icp | Parameter-free LiDAR odometry | Has a ROS 2 node; ideal GNSS-denied fallback. |
| FAST-LIO2 | https://github.com/hku-mars/FAST_LIO · ROS 2: https://github.com/Ericsii/FAST_LIO_ROS2 | Tightly-coupled LiDAR-inertial odometry | Core repo is ROS 1; use the ROS 2 port. |
| LIO-SAM | https://github.com/TixiaoShan/LIO-SAM | LiDAR-inertial SLAM w/ factor graphs | Reference architecture. |
| ORB-SLAM3 | https://github.com/UZ-SLAMLab/ORB_SLAM3 | Visual-inertial SLAM | Research-grade; study it. |
| GNSS/RTK (concept) | RAIM/FDE integrity literature | Fault detection for self-healing localization | See `04` C7. |

## C. Mapping, world model, traversability
| Project | Link | Use it for | Notes |
|---|---|---|---|
| grid_map | https://github.com/ANYbotics/grid_map | Multi-layer 2.5D grids (elevation, traversability, semantics) | Backbone of your world-model geometry. |
| elevation_mapping | https://github.com/ANYbotics/elevation_mapping | Robot-centric elevation w/ pose-drift handling | Great for rough ag terrain. |
| nvblox | https://github.com/nvidia-isaac/nvblox | GPU TSDF/ESDF 3D reconstruction | Ships a Nav2 costmap plugin. |
| isaac_ros_nvblox | https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox | ROS 2 wrapper for nvblox + Nav2 bridge | Migration bridge from costmap → world model. |
| OctoMap | https://github.com/OctoMap/octomap | 3D occupancy mapping | Classic reference. |
| Wild Visual Navigation | https://github.com/leggedrobotics/wild_visual_navigation | Online self-supervised visual traversability | Directly your P1.2 learned-traversability starting point. |
| FtFoot | https://github.com/yurimjeon1892/FtFoot | Self-supervised traversability from footprints (ICRA 2024) | Alternative self-supervision approach. |
| self_supervised_segmentation | https://github.com/leggedrobotics/self_supervised_segmentation | Unsupervised segmentation (STEGO) for off-road | Complements WVN. |

## D. Perception & computer vision (foundation/open-vocab)
| Project | Link | Use it for |
|---|---|---|
| Segment Anything (SAM) | https://github.com/facebookresearch/segment-anything | Promptable segmentation; auto-labeling. |
| Grounding DINO | https://github.com/IDEA-Research/GroundingDINO | Open-vocabulary detection ("find the person/animal"). |
| Grounded-SAM | https://github.com/IDEA-Research/Grounded-Segment-Anything | Open-vocab detect + segment; powerful auto-labeler. |
| CLIP | https://github.com/openai/CLIP | Image-text embeddings for open-vocab semantics. |
| MMDetection / MMsegmentation | https://github.com/open-mmlab/mmdetection | Detection/segmentation training toolboxes. |
| Ultralytics YOLO | https://github.com/ultralytics/ultralytics | Fast, practical detectors for onboard use. |
| OpenPCDet | https://github.com/open-mmlab/OpenPCDet | 3D LiDAR detection (PointPillars etc.). |
| Open3D | https://github.com/isl-org/Open3D | Point cloud processing. |

## E. Planning, control, prediction
| Project | Link | Use it for | Notes |
|---|---|---|---|
| Nav2 MPPI controller | https://github.com/ros-navigation/navigation2/tree/main/nav2_mppi_controller · docs: https://docs.nav2.org/configuration/packages/configuring-mppic.html | Your local planner; add **custom critics** for traversability/prediction/uncertainty | Lowest-risk high-impact upgrade path. |
| BehaviorTree.CPP | https://github.com/BehaviorTree/BehaviorTree.CPP | Behavior layer (Nav2 uses it) | Add health-reactive nodes. |
| Groot2 | https://www.behaviortree.dev/ | Visualize/edit behavior trees | Ops + debugging. |
| OMPL | https://github.com/ompl/ompl | Sampling-based motion planning library | For custom planners. |
| Trajectron++ | https://github.com/StanfordASL/Trajectron-plus-plus | Multimodal, map-aware trajectory prediction | Research-grade; adapt for people. |
| CasADi | https://github.com/casadi/casadi | Nonlinear optimization / NMPC | If you build MPC beyond MPPI. |
| acados | https://github.com/acados/acados | Fast embedded NMPC solvers | Real-time control. |
| Fields2Cover | https://github.com/Fields2Cover/Fields2Cover | **Coverage path planning for agriculture** | Directly ag-relevant — headland turns, swaths. |

## F. Simulation & synthetic data
| Project | Link | Use it for |
|---|---|---|
| Gazebo (Harmonic/Ionic) | https://gazebosim.org/ · https://github.com/gazebosim | Physics sim + CI; `ros_gz` bridge. |
| NVIDIA Isaac Sim | https://developer.nvidia.com/isaac/sim | Photoreal sensor sim, domain randomization, synthetic data. |
| Isaac ROS | https://github.com/NVIDIA-ISAAC-ROS | GPU-accelerated perception packages for Orin. |
| Isaac Lab | https://github.com/isaac-sim/IsaacLab | RL/learning in Isaac. |
| CARLA | https://github.com/carla-simulator/carla | AV sim; patterns transfer (not ag-specific). |
| BlenderProc | https://github.com/DLR-RM/BlenderProc | Procedural synthetic dataset generation. |

## G. Datasets (off-road, agriculture, driving)
| Dataset | Link | Contents |
|---|---|---|
| RELLIS-3D | https://github.com/unmannedlab/RELLIS-3D | Off-road multimodal (LiDAR+image) semantic segmentation. |
| RUGD | http://rugd.vision/ | Off-road semantic segmentation imagery. |
| Sugar Beets 2016 (Bonn) | https://www.ipb.uni-bonn.de/data/sugarbeets2016/ | Ag field robot: RGB-D, multispectral, crop/weed. |
| SB20 Sugar Beet (Bonn) | https://agrobotics.uni-bonn.de/sugar_beet_2020_dataset/ | RealSense nadir ground view, sugar beet field. |
| BonnBeetClouds3D | http://ipb.uni-bonn.de/data/bonnbeetclouds3d/ | UAV point clouds, organ-level phenotyping, 48 varieties. |
| Waymo Open (Perception+Motion) | https://waymo.com/open/ | State-of-the-art perception + trajectory prediction benchmarks. |
| nuScenes | https://www.nuscenes.org/ | Multimodal AV dataset (BEV, tracking, prediction). |
| Boreas | https://www.boreas.utias.utoronto.ca/ | Driving across seasons/weather (adverse conditions). |

## H. ML systems / MLOps / data engine
| Project | Link | Use it for |
|---|---|---|
| DVC | https://github.com/iterative/dvc | Dataset + pipeline versioning. |
| lakeFS | https://github.com/treeverse/lakeFS | Git-like versioning over object storage (scale). |
| MLflow | https://github.com/mlflow/mlflow | Experiment tracking + model registry. |
| TensorRT | https://developer.nvidia.com/tensorrt | Edge inference optimization (Orin). |
| ONNX Runtime | https://github.com/microsoft/onnxruntime | Portable model serving. |
| Triton Inference Server | https://github.com/triton-inference-server/server | Scalable model serving (cloud/offboard). |
| Label Studio | https://github.com/HumanSignal/label-studio | Human-in-the-loop labeling. |

## I. Cloud, fleet, distributed
| Project | Link | Use it for |
|---|---|---|
| Zenoh | https://github.com/eclipse-zenoh/zenoh | Robot↔cloud + multi-robot data flow over poor links. |
| Kubernetes | https://kubernetes.io/ | Cloud orchestration. |
| MinIO | https://github.com/minio/minio | S3-compatible object storage (data lake). |
| Prometheus + Grafana | https://prometheus.io/ · https://grafana.com/ | Metrics + dashboards. |
| VDA5050 (spec) | https://github.com/VDA5050/VDA5050 | AGV/AMR fleet interface standard (adapt for ag). |
| Open-RMF | https://github.com/open-rmf/rmf | Multi-robot fleet management framework (ROS 2). |

## J. Foundational papers (read with `06`'s "how to read a paper")
- **Occupancy/BEV:** Lift-Splat-Shoot; BEVFusion; occupancy networks (see arXiv).
- **Traversability (ag/off-road):** Wild Visual Navigation (arXiv:2404.07110 / 2305.08510); "Follow the Footprints" (FtFoot, ICRA 2024); WayFAST; BADGR.
- **Prediction:** Trajectron++ (arXiv:2001.03093); VectorNet; Waymo Sim Agents.
- **Planning:** MPPI (Williams et al., "Information-Theoretic MPC"); Experience Graphs (Phillips & Likhachev).
- **Estimation/SLAM:** FAST-LIO2; KISS-ICP; factor graphs (Dellaert & Kaess).
- **Safety:** SOTIF/ISO 21448 overviews; STPA (Leveson, "Engineering a Safer World").
- **Data engine:** Tesla AI Day talks (YouTube) — the clearest public window into auto-labeling + the loop.

## K. Ag-robotics research groups & venues to follow
- **University of Bonn** (Stachniss / PhenoRob) — ag perception, SLAM, datasets: https://www.ipb.uni-bonn.de/
- **ETH RSL** (Legged Robotics / off-road traversability): https://rsl.ethz.ch/
- **CMU Field Robotics Center**; **Oxford Robotics Institute**; **NVIDIA Robotics research**.
- **Venues:** CoRL, RSS, ICRA, IROS (robotics); CVPR/NeurIPS/ICLR (learning); *Journal of Field Robotics*, *Computers and Electronics in Agriculture* (ag).

---

## How to actually use this catalogue
1. For each Phase 0/1 task in `10-implementation-guide.md`, open the 1–2 linked repos, read their README + run their demo on public data **before** integrating.
2. Prefer the repo that (a) supports your ROS 2 distro, (b) has recent commits, (c) has a permissive license (check! — some research repos are non-commercial).
3. **License diligence is a CTO responsibility:** verify each dependency's license is compatible with a commercial product before it enters `ros2_ws`. Some datasets/models are research-only.
4. Contribute fixes upstream where you can — it builds your team's reputation and keeps your fork burden low.
