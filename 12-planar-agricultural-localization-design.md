# 12 — Planar Agricultural Localization Design (Aerial Map + RTK Commissioning + Learned Cross-View Features)

This document turns `01` Layer 3, `04` C7, and `10` P1.4 into an implementable design for one specific system: estimate the robot's **planar pose** `(x, y, yaw)` in a georeferenced site map, keep local motion smooth through GNSS-denied areas, and expose the result through the standard ROS 2 `map → odom → base_link` transform tree.

The target platform has two Livox Mid-360 LiDARs with IMUs, two RealSense D555 RGB-D cameras, wheel odometry, ordinary GNSS at runtime, LiDAR-inertial odometry (LIO), and a georeferenced aerial orthomosaic. RTK GNSS is permitted temporarily during commissioning and validation, but the deployed system must not depend on RTK, external tracking, artificial landmarks, or modifications to the site.

> **Decision summary.** Use LIO as the continuous local `odom → base_link` source. During RTK commissioning, build an optimized, georeferenced **robot-view reference map** and an aerial/ground training dataset. At runtime, localize primarily against the robot-view map for metric precision, use learned aerial/ground matching for global retrieval and recovery, fuse accepted SE(2) measurements in a robust fixed-lag estimator, and publish only `map → odom`. Learning solves association; explicit geometry and probabilistic estimation produce the pose and integrity estimate.

---

## 1. Scope, assumptions, and non-goals

### 1.1 Estimated state

The externally reported state is planar:

```text
X = [x_map, y_map, yaw_map]
```

Roll, pitch, and height are not global localization outputs. They may still be estimated internally by LIO because scan deskewing, gravity alignment, and operation on uneven ground require a full inertial attitude. The global localization layer projects the result onto SE(2).

### 1.2 Runtime inputs

| Input | Runtime role | Trust policy |
|---|---|---|
| LIO from the two Mid-360s and a designated master IMU | Smooth relative motion and short-term prediction | Primary local odometry; monitor degeneracy and covariance |
| Wheel increments/velocity | Low-frequency planar motion and nonholonomic information | Adaptive covariance; down-weight during slip |
| Ordinary GNSS | Coarse candidate restriction and recovery | Never a precision measurement; robustly gate multipath/outliers |
| Two D555 RGB streams | Semantics, appearance, learned descriptors | Condition-dependent; detect saturation, blur, darkness, and occlusion |
| Two D555 depth streams | Lift image features into local BEV | Range/confidence gated; not treated as survey-grade geometry |
| Two Mid-360 point streams | LIO, local geometry, scan-to-reference registration | Range/intensity/geometry gated; reject dust and vegetation dynamics |
| Aerial orthomosaic and optional DSM | Global geospatial prior and cross-view reference | Accuracy is bounded by survey and orthorectification quality |
| Commissioned robot-view map | Primary metric localization prior | Versioned; stable features only; monitor map age/change |

### 1.3 Commissioning-only inputs

- RTK GNSS observations, status, covariance, correction age, and antenna metadata.
- Optionally dual-antenna RTK heading. If unavailable, yaw is inferred from LIO plus RTK course over sufficiently long, straight motion.
- Repeated traversals in both directions and across representative operating conditions.

### 1.4 Hard constraints

- No total station, motion-capture system, fixed beacons, reflectors, AprilTags, or other external tracker.
- No permanent or temporary modification to the environment for runtime localization.
- RTK may be removed after commissioning.
- Runtime must expose uncertainty and ambiguity; it must not turn a visually plausible match into an overconfident pose.
- Local motion must remain continuous even when global localization corrects drift.

### 1.5 Non-goals

- Guaranteed sub-centimeter absolute accuracy everywhere.
- Full 6-DoF global localization.
- Replacing LIO with the learned model.
- Training an end-to-end network that directly commands the robot or directly regresses unbounded global coordinates.
- Treating the aerial image as error-free ground truth.

---

## 2. Feasibility and the accuracy claim

This architecture is feasible and can deliver robust map-relative planar localization without permanent infrastructure. It can plausibly reach centimetre-class repeatability near persistent geometry after a high-quality commissioning run. It cannot honestly guarantee sub-centimeter **absolute** accuracy from the stated sensors and map.

Keep four concepts separate:

1. **Local precision:** how smoothly and consistently LIO estimates motion over seconds.
2. **Map-relative repeatability:** whether the robot returns to the same physical line on repeated visits.
3. **Absolute geodetic accuracy:** whether the reported coordinate agrees with an external geodetic reference.
4. **Integrity:** whether the system knows when the first three claims are not trustworthy.

A learned network may estimate a subpixel alignment, but it cannot remove unknown orthomosaic distortion, RTK label bias, sensor extrinsic error, timestamp error, or physical map change. The production requirement must therefore include accuracy, availability, and integrity. A reasonable first validation gate is:

| Metric | Initial engineering target | Notes |
|---|---:|---|
| Horizontal map error, commissioned routes | `< 5 cm` at 95th percentile | Tighten only after measured evidence |
| Yaw error | `< 0.5°` at 95th percentile | Evaluate separately from position |
| Relative lateral repeatability | `< 2 cm` at 95th percentile | May outperform absolute geodetic accuracy |
| False-confident localization | `0` in the validation corpus | A wrong confident update is worse than no update |
| Localization availability | `> 99%` inside the declared ODD | `LOCALIZED` or bounded `DEGRADED`, not merely a pose topic |
| TF publication | Continuous at control-compatible rate | Global corrections must not break local control |

These are proposal-level targets, not guaranteed sensor specifications. Establish the final numbers from an error-budget audit and held-out RTK validation.

---

## 3. Coordinate frames and the ROS 2 TF contract

### 3.1 Frame definitions

Use REP-105 semantics:

```text
earth/ECEF
└── map                         fixed local ENU site frame
    └── odom                    continuous local frame; globally corrected
        └── base_link           robot body reference
            ├── lidar_front
            ├── lidar_rear
            ├── camera_left
            ├── camera_right
            └── gnss_antenna
```

| Frame | Definition | Authority |
|---|---|---|
| `earth` | Geocentric or geodetic parent when multi-site support is needed | Static geodesy/map service |
| `map` | Local East-North-Up metric frame with recorded datum and origin | Map service; never silently changed |
| `odom` | Locally smooth frame initialized for the mission | Global localization node publishes its parent correction |
| `base_link` | Fixed robot reference point | LIO publishes its pose under `odom` |
| Sensor frames | Rigid calibrated frames | `robot_state_publisher` or static TF publisher |

Store the map origin as latitude, longitude, ellipsoidal height, datum, projection/CRS, geoid handling, and map version. Never optimize directly in latitude/longitude degrees. Use GDAL/PROJ or an equivalent audited geodesy library to transform orthomosaic coordinates and GNSS fixes into local ENU metres.

### 3.2 Single-authority rule

There must be exactly one dynamic publisher for each TF edge:

```text
LIO:                  odom → base_link
Global localizer:     map  → odom
Static calibration:   base_link → each sensor
```

Do **not** broadcast a second dynamic `map → base_link` edge. TF is a tree; `base_link` cannot have both `map` and `odom` as parents.

### 3.3 Transform computation

At measurement timestamp `t`, the global localizer estimates the robot pose in the map frame:

```text
T_map_base(t) = SE2(x, y, yaw)
```

It retrieves the time-aligned LIO transform:

```text
T_odom_base(t)
```

Then computes:

```text
T_map_odom(t) = T_map_base(t) · inverse(T_odom_base(t))
```

The localizer broadcasts `T_map_odom`. Any consumer obtains the robot pose using:

```cpp
lookupTransform("map", "base_link", stamp)
```

In tf2 language, that returns the pose of `base_link` expressed in `map`, commonly described as the `map → base_link` transform. A component that literally requires `base_link → map` must request the reverse lookup or invert the result; no additional broadcaster is needed.

### 3.4 Planar projection

LIO may publish a full SE(3) `odom → base_link`. The global correction is planar:

```text
z = 0
roll = 0
pitch = 0
yaw = estimated map yaw correction
```

For consumers requiring a strictly planar robot pose, publish an additional `PoseWithCovarianceStamped` or `Odometry` message containing `(x, y, yaw)` and a 3×3 covariance. Do not distort the physical sensor TF tree merely to force the robot onto a mathematical plane.

### 3.5 Correction behavior

- `odom → base_link` must never jump.
- `map → odom` may change when a global observation is accepted, as REP-105 permits.
- Rate-limit or filter correction delivery for visualization and planning if needed, but do not hide a large localization inconsistency from the integrity monitor.
- Compute transforms at the measurement timestamp, not at callback receipt time.
- Re-broadcast the latest optimized correction at a stable rate while preserving its source timestamp and diagnostic age.

---

## 4. Sensor front end and calibration

### 4.1 Two-LiDAR LIO strategy

Use one coherent local odometry authority. Preferred architecture:

1. Designate one Mid-360 IMU as the master inertial source.
2. Hardware-time or tightly software-time synchronize both LiDAR point streams and the master IMU.
3. Calibrate `T_base_lidar_1`, `T_base_lidar_2`, `T_lidar_1_imu_master`, and all time offsets.
4. Deskew points using the master LIO trajectory.
5. Transform both point streams into a shared frame before scan-to-map residual construction.
6. Emit one `odom → base_link` estimate and one covariance/health report.

An acceptable first milestone is primary-LiDAR LIO plus the secondary LiDAR used only for downstream local mapping. Add raw dual-LiDAR fusion after the single-LiDAR pipeline is stable.

Do not run two independent LIO systems and fuse their pose outputs as if they were independent Gaussian measurements. They observe the same motion and much of the same scene; unknown correlation can create severe overconfidence.

### 4.2 Wheel odometry

Prefer raw wheel/steering increments or body-frame velocity over a separately integrated global wheel pose. Estimate:

- Encoder scale.
- Track width or steering geometry.
- Steering offset.
- Effective rolling radius by terrain/load if necessary.
- Slip indicators from wheel/LIO velocity disagreement, IMU lateral acceleration, and motor current.

Inflate wheel covariance during mud, loose soil, aggressive turns, or high slip. A nonholonomic lateral-velocity constraint can help on firm ground, but must be relaxed for skid steer and side slip.

### 4.3 RGB-D cameras

Calibrate:

- Intrinsics and distortion for RGB and depth.
- Factory RGB-depth alignment verification.
- `T_base_camera_left` and `T_base_camera_right`.
- Camera-to-LiDAR extrinsics.
- Timestamp offsets and exposure delay.

Use depth confidence/range masks. Direct sunlight, low-texture surfaces, reflective polytunnel material, dust, and range all affect stereo depth. The cameras provide semantic and learned cross-view evidence; they are not the absolute reference.

### 4.4 GNSS lever arm and metadata

Store the full rigid transform from `base_link` to the GNSS antenna. Convert an antenna measurement into a base-link constraint using the current yaw estimate. Retain:

- Fix type: no fix, SPS, DGPS, RTK float, RTK fixed.
- Receiver covariance and DOP.
- Correction age and baseline where available.
- Satellite count and constellation status.
- Raw timestamp and time reference.

During runtime, ordinary GNSS is a broad prior and fault-recovery aid. During commissioning, only quality-gated RTK-fixed observations should become strong labels.

### 4.5 Timing error budget

A timestamp error produces a position error approximately equal to:

```text
position_error ≈ robot_speed × time_error
```

At `2 m/s`, a `5 ms` offset creates `10 mm` of apparent displacement before considering rotation. Record per-sensor timestamp provenance and measure, rather than assume, synchronization quality. PTP/PPS or hardware triggers are preferred; software receipt timestamps are not sufficient for precision mapping.

### 4.6 Calibration acceptance

Calibration is an artifact, not a one-time terminal command. Version:

```text
calibration/
├── intrinsics/
├── extrinsics/
├── time_offsets/
├── wheel_model/
├── gnss_lever_arm/
├── reports/
└── calibration_manifest.yaml
```

Every artifact records robot ID, sensor serials, method, dataset, result covariance/residuals, operator, date, software commit, and expiration/recheck rule. Reject commissioning data if calibration or timing health is unknown.

---

## 5. Map products and map truth

### 5.1 Required aerial artifact

The orthomosaic should be a GeoTIFF or equivalent raster with:

- Explicit CRS and datum.
- Affine pixel-to-map transform.
- Ground sampling distance (GSD).
- Acquisition date and season.
- Orthorectification method.
- RTK/PPK/GCP survey report where available.
- Independent checkpoint error, not only training/GCP residual.
- Nodata/invalid mask.

If a DSM/DTM or photogrammetric point cloud exists, preserve it. Although the global output is planar, height helps separate roofs, vegetation, ground, and polytunnel structure when generating semantics.

### 5.2 Semantic map layers

Create a shared class ontology designed around persistence and observability:

| Class | Expected stability | Typical localization value |
|---|---:|---|
| Building footprint/corner | High | Strong `x/y/yaw` anchor |
| Masonry wall | High | Strong perpendicular constraint; weak along an isolated straight wall |
| Fence line/post cluster | Medium-high | Useful if visible and not vegetation-obscured |
| Road/hard-surface boundary | Medium-high | Good long-term edge; width/appearance may change |
| Polytunnel entrance/end | Medium-high | Strong longitudinal disambiguation |
| Polytunnel frame/centerline | Medium | Strong lateral/yaw; repeated frames are longitudinally ambiguous |
| Drain/ditch/berm | Medium | Useful geometry, seasonal appearance risk |
| Mature tree trunk cluster | Medium | Better in LiDAR than aerial canopy; map association must be cautious |
| Crop row/vegetation boundary | Low-seasonal | Useful short term; not a permanent global anchor |
| Soil texture/shadow/plastic cover | Low | Never a sole precision anchor |

Generate vector primitives, class-specific distance transforms, and multi-resolution raster pyramids. Attach a covariance or confidence to every map primitive. Map uncertainty must appear in the measurement covariance; it is not an offline concern that disappears at runtime.

### 5.3 Robot-view reference map

The commissioned reference map is the primary precision layer. Store tiled, versioned keyframes/submaps:

```text
field_map_vN/
├── manifest.yaml                # site, ENU origin, CRS, date, software/calibration versions
├── aerial/
│   ├── orthomosaic.tif
│   ├── semantics.tif
│   └── vectors.geojson
├── ground/
│   ├── lidar_submaps/
│   ├── rgb_keyframes/
│   ├── semantic_bev/
│   ├── descriptors/
│   └── keyframes.parquet
├── topology/
│   └── places_and_routes.geojson
├── uncertainty/
│   ├── map_covariance.tif
│   └── alignment_report.json
└── checksums.json
```

Each ground keyframe includes optimized SE(2) pose/covariance, sensor timestamps, calibration version, RTK quality contribution, season/lighting metadata, feature quality, and links to source logs. Never overwrite a deployed map in place; release a new immutable map version.

### 5.4 Aerial-to-RTK alignment

A georeferenced aerial map and RTK trajectory may have a systematic offset or rotation. Before producing training labels:

1. Transform both into the same documented datum and local ENU frame.
2. Identify stable aerial/ground correspondences or align stable semantic edges.
3. Estimate a robust site-level SE(2) or similarity transform.
4. Evaluate independent checkpoints/held-out trajectories.
5. Preserve the transform and residual field in the map manifest.

A spatial warp may reduce photogrammetric distortion, but it can also manufacture apparent accuracy. Use only a low-complexity, regularized warp supported by distributed independent evidence, and report both pre- and post-warp errors. Never fit and evaluate on the same trajectories.

---

## 6. RTK commissioning workflow

### 6.1 Data collection plan

Collect multiple sessions rather than one perfect-looking drive:

- Traverse every operational route in both directions.
- Include headlands, intersections, building edges, roads, tunnel entrances, and each polytunnel.
- Drive loops that return to distinctive areas.
- Vary speed while remaining inside the target ODD.
- Capture morning/noon/evening lighting where camera localization matters.
- Include representative bare-soil, crop-growth, wet/dry, and covered/uncovered tunnel conditions when practical.
- Repeat a subset on a different day for held-out validation.

Record raw sensors, `/tf_static`, provisional `/tf`, calibration IDs, RTK status, correction metadata, commands, and health. MCAP logs are immutable source data.

### 6.2 RTK quality gates

A commissioning RTK sample is label-eligible only if it satisfies configured gates such as:

- RTK fixed, not float.
- Position covariance below the project threshold.
- Correction age below the receiver-specific limit.
- No innovation jump against LIO prediction.
- Sufficient satellite/geometry indicators when available.
- Antenna lever arm and timestamp known.

Rejected RTK is retained for diagnosis but does not become a strong graph factor or training label.

### 6.3 Yaw observability

A single RTK antenna does not observe yaw while stationary. If dual-antenna heading is unavailable, estimate heading using a joint trajectory:

- LIO supplies high-rate relative yaw.
- Wheel/nonholonomic constraints stabilize planar motion where valid.
- RTK position displacement supplies course over ground only over windows with adequate speed and displacement.
- Reverse motion and turns are modeled explicitly; velocity direction is not always body forward.
- Straight traversals in both directions reduce bias.

Do not create yaw labels by differencing adjacent noisy RTK points. Gate course-derived yaw by baseline length, motion model, curvature, and RTK covariance.

### 6.4 Commissioning pose graph

Optimize keyframe states:

```text
X_k = [x_k, y_k, yaw_k]
```

Suggested factors:

- Relative SE(2) factor from LIO keyframes.
- Wheel/body velocity or relative-motion factor with slip-dependent covariance.
- RTK antenna position factor with lever-arm compensation.
- Course/heading factor when observable.
- LiDAR scan/submap loop closures.
- Visual/semantic loop closures where verified.
- Weak motion priors only where physically justified.

Use robust losses and switchable/dynamic constraints for potentially false loop closures. Preserve the marginal pose covariance per keyframe. The optimized trajectory, not raw RTK samples, labels the synchronized multimodal data.

### 6.5 Polytunnel commissioning

RTK may degrade inside a tunnel. Anchor each tunnel by:

1. Obtaining high-quality RTK outside the entrance.
2. Entering with initialized LIO.
3. Traversing the full tunnel while accumulating LiDAR/RGB-D submaps.
4. Exiting to a high-quality RTK region when topology permits.
5. Repeating in the reverse direction.
6. Closing loops at entrances, ends, and distinctive cross-aisles.
7. Jointly optimizing all passes.

The resulting interior labels are inferred through a constrained trajectory and carry larger covariance than directly RTK-observed outdoor poses. That covariance must flow into training and map matching.

### 6.6 Dataset generation and split discipline

For each optimized keyframe:

- Extract an aerial tile around the pose at one or more metric scales.
- Build a synchronized temporal robot BEV.
- Store target `dx`, `dy`, and `dyaw` relative to tile center/orientation.
- Store pose covariance, map uncertainty, visibility mask, and condition metadata.
- Generate hard negatives from nearby repeated rows/tunnels and visually similar remote locations.

Split by **route, day, and condition**, not random frames. Adjacent frames are nearly duplicates; random frame splitting will produce misleading test accuracy. Keep at least one complete route/day as an untouched final validation set.

---

## 7. Cross-view and same-view learned localization

### 7.1 Why use two localization paths

The system should not bet everything on the hardest modality gap.

**Same-view path — primary precision:**

```text
live LiDAR/RGB-D BEV ↔ commissioned ground LiDAR/RGB-D map
```

This path sees approximately the same structures from approximately the same sensor height and is the strongest source for fine metric registration.

**Cross-view path — global retrieval and recovery:**

```text
live ground LiDAR/RGB-D BEV ↔ aerial RGB/semantic map
```

This path covers uncommissioned gaps and enables relocalization from the preloaded aerial map, but carries larger viewpoint, occlusion, season, and map-projection uncertainty.

### 7.2 Robot temporal BEV

At a keyframe, accumulate a short time window using LIO:

1. Deskew LiDAR points.
2. Transform both LiDAR and RGB-D observations into `base_link` or a gravity-aligned local frame.
3. Segment RGB images into the shared stable-class ontology.
4. Back-project valid semantic/deep image features using depth.
5. Remove or reduce weight for dynamic objects, crops, leaves, dust, sky, and uncertain depth.
6. Rasterize metric BEV channels.

Candidate BEV channels:

```text
occupancy / point density
min, max, mean, variance of height
surface normals or verticality
LiDAR intensity statistics
RGB features
semantic class probabilities
visibility / observation count
per-cell uncertainty
```

Use a fixed metric extent and resolution appropriate to site geometry and compute budget. Do not lock these values before inspecting point density and aerial GSD.

### 7.3 Aerial representation

Build a metric north-aligned feature pyramid from:

- Orthomosaic RGB.
- Semantic probability maps.
- Stable vector-edge distance transforms.
- Optional DSM height/normal channels.
- Map uncertainty and invalid masks.

The encoder must know metric scale. Data augmentation may rotate/crop/photometrically alter tiles, but must update pose labels exactly.

### 7.4 Coarse retrieval model

Train aerial and robot encoders with a contrastive objective so corresponding places have nearby descriptors. The output is a candidate list or heatmap, not a final pose.

Use hard negatives aggressively:

- Adjacent identical polytunnels.
- The same relative position in neighboring crop rows.
- Repeated building facades.
- Locations separated by one tunnel-frame or row period.
- Visually similar roads at different site coordinates.

Ordinary GNSS can restrict the candidate set, but training and evaluation must include GNSS-denied and biased-prior cases. Otherwise the network may appear successful while relying on the prior rather than visual/geometric evidence.

### 7.5 Fine SE(2) correlation model

For each candidate, evaluate a local cost volume:

```text
C(Δx, Δy, Δyaw)
```

Use differentiable feature correlation, rotated feature sampling, or a learned matching head. Return:

- Most likely correction.
- Full or approximated probability distribution.
- Covariance/Hessian estimate.
- Peak ratio and entropy.
- Supporting correspondence/attention visualization.

A distribution is essential: repeated rows and tunnel frames naturally create multiple valid peaks. A direct coordinate-regression network tends to average modes or hide ambiguity.

### 7.6 Training losses

A practical combined objective is:

```text
L = λ_retrieval L_contrastive
  + λ_pose      L_SE2_distribution
  + λ_metric    L_correspondence_geometry
  + λ_unc       L_uncertainty_calibration
  + λ_temp      L_temporal_consistency
```

Where:

- `L_contrastive` separates correct and hard-negative places.
- `L_SE2_distribution` is classification/NLL over the local pose grid or a mixture-density loss.
- `L_correspondence_geometry` penalizes inconsistent matched stable primitives.
- `L_uncertainty_calibration` prevents overconfident wrong matches.
- `L_temporal_consistency` requires sequential outputs to agree with LIO motion.

Weight training samples by commissioning pose and map uncertainty. Do not train low-confidence tunnel-interior labels as if they were equal to direct RTK-fixed outdoor labels.

### 7.7 Geometric refinement

Learning proposes candidate correspondences; explicit geometry refines pose. Depending on the available map layer:

- Point-to-plane or generalized ICP against commissioned LiDAR submaps.
- Point-to-line residuals for walls, fences, road edges, and tunnel centerlines.
- Point-to-point residuals for stable corners/posts with robust kernels.
- Semantic class consistency to prevent a crop edge matching a building edge.
- Multi-resolution registration from coarse to fine.

Estimate covariance from residual geometry, map uncertainty, and local observability. Registration along one long wall may tightly constrain perpendicular position and yaw while remaining weak along the wall; the covariance must represent this anisotropy.

### 7.8 Model lifecycle

- Train offboard with versioned MCAP-derived datasets.
- Track data, code, model, map, calibration, and metrics together.
- Export ONNX/TensorRT only after numerical parity tests.
- Run new models in shadow mode before they can add estimator factors.
- Monitor embedding drift, match entropy, and per-condition performance.
- Retain a deterministic semantic/geometric baseline when ML is unavailable.

---

## 8. Runtime localization and estimator

### 8.1 Runtime sequence

```text
1. LIO predicts continuous odom → base_link
2. Wheel data updates slip/motion health
3. Normal GNSS defines a broad candidate region when trustworthy
4. Ground-map descriptor retrieval proposes commissioned submaps
5. Cross-view aerial retrieval proposes backup/global candidates
6. Fine SE(2) correlation scores each candidate
7. Geometric/semantic refinement estimates pose + covariance
8. Integrity gates accept, defer, or reject each measurement
9. Fixed-lag SE(2) estimator updates map pose hypotheses
10. TF publisher computes and broadcasts map → odom
```

### 8.2 State and process model

At keyframe `k`:

```text
X_k = [x_k, y_k, yaw_k]
```

The LIO relative measurement is projected into SE(2):

```text
z_lio,k = Log_SE2(inverse(X_{k-1}) · X_k) + noise
```

Preserve the relative covariance and cross-correlation assumptions. If LIO covariance is unavailable or unreliable, characterize it empirically by terrain and geometry class rather than inventing a small constant covariance.

### 8.3 Measurement factors

| Factor | Residual | Treatment |
|---|---|---|
| LIO relative pose | SE(2) between-pose error | Main process/odometry factor |
| Wheel increment/velocity | Body-frame planar motion error | Slip-adaptive; avoid double-integrated pose |
| Ordinary GNSS | ENU antenna position error | Large covariance, robust loss, multipath gating |
| Ground-map match | SE(2) pose error | Strongest absolute factor when geometry/score gates pass |
| Aerial cross-view match | SE(2) pose error | Larger map/model covariance; often coarse/recovery factor |
| Semantic primitive | Point-to-line/point residual | Class- and map-uncertainty weighted |
| Heading/course | Wrapped yaw error | Only when observable and quality gated |

Use a fixed-lag smoother for temporal robustness and delayed map-match measurements. GTSAM is a suitable implementation target; a simpler EKF/particle prototype is acceptable only if it preserves multimodal recovery and honest uncertainty.

### 8.4 Avoiding double counting

- Do not add the Mid-360 IMU again as an independent global factor if the same IMU is already fully consumed by LIO, unless the estimator is redesigned as one tightly coupled graph with correct correlations.
- Do not fuse an integrated wheel pose and its source increments simultaneously.
- Do not treat consecutive overlapping temporal BEV matches as independent. Keyframe or covariance-inflate them.
- Do not treat both LiDAR-derived LIO and LiDAR scan-to-map errors as independent without accounting for shared points; robust fixed-lag estimation and conservative covariance are required.

### 8.5 Multi-hypothesis tracking

Polytunnels and crop rows can produce aliases separated by a structural period. Maintain multiple hypotheses when the cost volume has comparable peaks:

```text
H_i = {pose_i, covariance_i, weight_i, age_i, supporting_evidence_i}
```

Propagate each with LIO, update weights with new independent observations, merge near-identical hypotheses, and prune only when probability and integrity rules permit. Distinctive entrances, ends, buildings, junctions, and road transitions usually resolve ambiguity.

Never collapse to one hypothesis merely because downstream software expects one pose. Publish the best safe pose only when dominance criteria pass; otherwise remain in `AMBIGUOUS` or `DEGRADED_ODOMETRY_ONLY` mode.

### 8.6 Localization modes

| Mode | Meaning | Allowed behavior |
|---|---|---|
| `INITIALIZING` | Datum/map loaded; no accepted global hypothesis | Stationary or low-speed search behavior |
| `LOCALIZED` | Unique, consistent global hypothesis with bounded protection level | Normal operation inside ODD |
| `DEGRADED_ODOMETRY_ONLY` | Global update unavailable; LIO remains healthy | Reduced speed/time/distance budget |
| `AMBIGUOUS` | Multiple credible map hypotheses | Continue only under bounded odometry and safe route policy |
| `RELOCALIZING` | Active broad candidate search | Stop or crawl according to hazard analysis |
| `LOST` | No bounded pose claim | Safe stop and operator escalation |

---

## 9. Integrity monitoring and safe acceptance

### 9.1 Measurement innovation gate

For a candidate map measurement `z` with predicted measurement `h(X)`, compute:

```text
ν = z - h(X)
S = H P Hᵀ + R
NIS = νᵀ S⁻¹ ν
```

Use a chi-square gate appropriate to measurement dimension, but do not rely on NIS alone. A false map match can be self-consistent if the prior drifted toward the wrong repeated structure.

### 9.2 Map-match acceptance gates

Require a configured combination of:

- Best-to-second-best score ratio.
- Low enough pose-distribution entropy.
- Sufficient inlier count and spatial distribution.
- Geometric residual below class/range-dependent threshold.
- Observability eigenvalues above thresholds in required directions.
- Agreement between camera, LiDAR, and semantics where available.
- Agreement with LIO prediction within an integrity bound.
- Temporal persistence over multiple keyframes.
- Candidate not entirely supported by low-stability classes.
- Map and model versions approved for the robot/site.

### 9.3 Protection levels

Covariance is not a safety guarantee, especially with data-association failures. Publish conservative horizontal and yaw protection levels derived from:

- Estimator covariance.
- Recent innovation consistency.
- Map-match ambiguity.
- Map uncertainty.
- Time since last trusted global update.
- LIO degradation rate under current geometry.
- Known calibration and timing bounds.

Behavior planning should consume protection levels and localization mode, not a hand-wavy confidence scalar alone.

### 9.4 Correction sanity

A large accepted correction requires stronger evidence. Configure thresholds for:

- Maximum one-step translation/yaw correction in normal tracking.
- Recovery-only large correction with independent confirmation.
- Maximum correction rate delivered to non-safety consumers.
- Map/odom discrepancy that triggers event logging and map review.

Every rejection, hypothesis switch, mode transition, and accepted correction must be logged with reason codes and supporting metrics.

---

## 10. ROS 2 software architecture

### 10.1 Package layout

Extend the implementation-guide monorepo with:

```text
ros2_ws/src/
├── jabas_interfaces/
│   ├── msg/
│   │   ├── LocalizationStatus.msg
│   │   ├── LocalizationHypothesis.msg
│   │   ├── LocalizationHypothesisArray.msg
│   │   ├── MapMatch.msg
│   │   └── SensorIntegrity.msg
│   └── srv/
│       ├── Relocalize.srv
│       ├── SetLocalizationMode.srv
│       └── GetMapMetadata.srv
├── jabas_localization/
│   ├── jabas_lio_adapter/
│   ├── jabas_local_submap/
│   ├── jabas_place_recognition/
│   ├── jabas_crossview_localizer/
│   ├── jabas_map_registration/
│   ├── jabas_planar_fusion/
│   ├── jabas_localization_integrity/
│   └── jabas_localization_bringup/
├── jabas_map_tools/
│   ├── jabas_geodesy/
│   ├── jabas_map_compiler/
│   └── jabas_map_validator/
└── jabas_calibration/
    ├── jabas_spatial_calibration/
    └── jabas_temporal_calibration/

ml/localization/
├── datasets/
├── aerial_encoder/
├── robot_bev_encoder/
├── se2_correlation/
├── uncertainty_calibration/
├── evaluation/
└── export/

tools/localization/
├── commission_site.py
├── build_ground_map.py
├── generate_crossview_dataset.py
├── replay_localization.py
└── evaluate_localization.py
```

### 10.2 Node responsibilities

| Node/component | Responsibility |
|---|---|
| `lio_adapter` | Normalize LIO pose, covariance, health, and timestamp contract; does not own global TF |
| `sensor_integrity` | Validate timing, frame availability, camera/depth/LiDAR/GNSS health |
| `local_submap_builder` | Build deskewed temporal LiDAR/RGB-D/semantic BEV keyframes |
| `place_recognition` | Retrieve commissioned ground-map candidates |
| `crossview_localizer` | Retrieve and correlate robot BEV against aerial features |
| `map_registration` | Geometric/semantic SE(2) refinement and covariance estimation |
| `planar_fusion` | Fixed-lag estimation, hypothesis management, and `T_map_base` estimate |
| `localization_integrity` | Gates measurements, computes protection levels/mode, emits diagnostics |
| `map_odom_broadcaster` | Time-aligned `T_map_odom = T_map_base · T_odom_base⁻¹` publication |
| `map_server` | Loads immutable map version, tiles, descriptors, metadata, and uncertainty |

The broadcaster may be integrated into `planar_fusion`, but its TF ownership and timestamp contract must remain explicit.

### 10.3 Topic and service contract

Suggested interfaces:

```text
Inputs
  /lio/odometry                         nav_msgs/Odometry
  /lio/health                           custom status or diagnostics
  /wheel/odometry                       nav_msgs/Odometry or TwistWithCovarianceStamped
  /gnss/fix                             sensor_msgs/NavSatFix
  /gnss/status                          receiver-specific normalized status
  /lidar/front/points                   sensor_msgs/PointCloud2
  /lidar/rear/points                    sensor_msgs/PointCloud2
  /camera/left/color, /depth            sensor_msgs/Image
  /camera/right/color, /depth           sensor_msgs/Image
  /tf, /tf_static

Outputs
  /localization/pose                    geometry_msgs/PoseWithCovarianceStamped
  /localization/status                  jabas_interfaces/LocalizationStatus
  /localization/hypotheses              jabas_interfaces/LocalizationHypothesisArray
  /localization/map_match               jabas_interfaces/MapMatch
  /localization/protection_level        custom message or fields in status
  /localization/diagnostics              diagnostic_msgs/DiagnosticArray
  /tf                                   map → odom

Services/actions
  /localization/relocalize
  /localization/reset_odom_alignment
  /localization/set_initial_pose
  /localization/get_map_metadata
```

### 10.4 Minimal status fields

`LocalizationStatus` should include:

```text
Header header
uint8 mode
string map_id
string map_version
string model_version
float64 horizontal_protection_level_m
float64 yaw_protection_level_rad
float64 age_of_last_global_update_s
float64 best_hypothesis_probability
float64 ambiguity_ratio
bool lio_healthy
bool wheel_healthy
bool gnss_healthy
bool ground_map_match_healthy
bool aerial_match_healthy
string[] active_faults
string[] recent_rejection_reasons
```

### 10.5 QoS and lifecycle

- Sensor streams: sensor-data QoS, bounded queues, no stale backlog.
- Map metadata/model version: reliable and transient-local.
- Localization pose/status: reliable with small depth; timestamp every state.
- Diagnostics: reliable but lower rate.
- Components are lifecycle-managed. Activation requires calibration, map, TF, model compatibility, and time-sync checks to pass.
- Use composition/intra-process communication for point clouds and images to control copies and latency.

### 10.6 Configuration contract

Parameters must be versioned per robot/site and grouped by concern:

```text
config/
├── frames.yaml
├── geodesy.yaml
├── calibration_manifest.yaml
├── lio_adapter.yaml
├── keyframes.yaml
├── retrieval.yaml
├── registration.yaml
├── fusion.yaml
├── integrity.yaml
├── runtime_modes.yaml
└── model_manifest.yaml
```

Do not hide safety-relevant thresholds in source code. Every threshold has units, rationale, owner, validation evidence, and allowed range.

---

## 11. Accuracy and observability budget

### 11.1 Principal contributors

| Contributor | Error mechanism | Control |
|---|---|---|
| Aerial map georeferencing | Global translation/rotation and local warp | Survey report, independent checks, robust alignment |
| Aerial GSD/orthorectification | Pixel quantization, parallax, roof/terrain displacement | Metric feature layers, avoid roof-edge misuse, map covariance |
| RTK commissioning | Fix ambiguity, multipath, datum, antenna lever arm | Fixed-only gates, metadata, smoothing, held-out validation |
| LIO | Drift, geometric degeneracy, IMU bias | Dual-view geometry, health metrics, loops, regular global updates |
| Wheel odometry | Slip and calibration | Adaptive covariance, compare with LIO/IMU |
| LiDAR ranging/registration | Range noise, incidence, dust, vegetation, map change | Multi-point robust geometry, stable-class masks, residual checks |
| RGB-D | Depth bias and environmental sensitivity | Confidence/range masks; use mainly for semantics/features |
| Spatial calibration | Lever-arm error couples yaw into position | Repeatable calibration with covariance and recheck policy |
| Time synchronization | Motion turns delay into position/yaw error | Hardware time, measured offsets, latency monitoring |
| Learned association | Domain shift and aliasing | Hard negatives, uncertainty calibration, multimodal hypotheses |
| Map aging | Structures/crops change | Versioned updates, change detection, per-feature stability |

### 11.2 Yaw-to-position coupling

A yaw error acting over lever arm or lookahead `L` creates lateral error approximately:

```text
lateral_error ≈ L × yaw_error_rad
```

At `L = 5 m`, `0.1° ≈ 1.745 mrad` produces about `8.7 mm` lateral error. A sub-centimeter tool-path requirement therefore imposes a tight yaw and lever-arm requirement even when robot-centre `(x,y)` appears accurate.

### 11.3 Geometry-specific observability

- One straight wall: strong perpendicular position and yaw; weak translation along the wall.
- Parallel crop rows: strong lateral and yaw; weak longitudinal position.
- Repeated tunnel frames: multiple longitudinal modes separated by frame spacing.
- Building corner or T-junction: good planar observability.
- Open uniform field: little map-relative observability; rely on odometry/GNSS until distinctive features appear.
- Tunnel entrance/end: valuable mode-disambiguation landmark without artificial modification.

The registration output must include directional covariance/eigenvalues. A scalar score cannot describe observability.

### 11.4 Precision versus absolute accuracy

The commissioned ground map may enable excellent repeated-path precision even if the whole map is shifted several centimetres in the geodetic frame. Decide which business requirement matters:

- Absolute coordinate accuracy for interoperability.
- Repeatable tool placement relative to rows.
- Lateral path error.
- Map-to-map consistency across robots.

Report all relevant metrics; do not summarize them as “sub-centimeter localization.”

---

## 12. Implementation roadmap and acceptance gates

### Phase L0 — Requirements, ODD, and data contract (2–3 weeks)

**Build:**

- Define map origin/CRS, frames, TF authorities, timestamps, pose convention, covariance convention, and localization modes.
- Define accuracy, yaw, availability, false-confidence, startup, and recovery metrics.
- Inventory exact sensor firmware, rates, fields of view, networking, and compute.
- Create the canonical MCAP topic set and metadata manifest.

**Acceptance:**

- TF graph has one authority per edge.
- A recorded bag can be transformed into a common time/frame domain without extrapolation errors.
- Requirements state percentile, conditions, reference, and failure behavior.

### Phase L1 — Calibration and baseline local odometry (4–8 weeks)

**Build:**

- Validate primary Mid-360 LIO and covariance/health.
- Add secondary LiDAR to mapping, then to LIO only after measured benefit.
- Calibrate all spatial/temporal transforms and wheel model.
- Implement slip and sensor-integrity monitors.

**Acceptance:**

- Repeated closed loops quantify translational/yaw drift.
- Timing perturbation tests show monitor sensitivity.
- Calibration reports and manifests are reproducible.
- `odom → base_link` is smooth under GNSS loss.

### Phase L2 — Map compiler and deterministic baseline (4–8 weeks)

**Build:**

- Import GeoTIFF/DSM, establish ENU, compile semantic/vector/distance layers.
- Implement GNSS-restricted semantic edge correlation.
- Implement multi-resolution geometric registration where 3D prior exists.
- Publish planar pose, covariance, diagnostics, and correct `map → odom` TF.

**Acceptance:**

- Known synthetic map transforms are recovered within tolerance.
- Repeated structures produce ambiguity rather than false certainty.
- Normal GPS outliers do not pull a valid map match.

### Phase L3 — RTK commissioning mapper (6–10 weeks)

**Build:**

- Quality-normalize RTK and implement lever-arm factors.
- Build the commissioning pose graph with LIO, wheels, RTK, and loops.
- Generate tiled ground reference maps and uncertainty.
- Establish aerial-to-RTK alignment and independent checks.

**Acceptance:**

- Held-out RTK residuals satisfy the chosen commissioning-map target.
- Bidirectional tunnel traversals align without using tunnel-interior RTK as false truth.
- Every ground keyframe traces to source log, calibration, map, and optimizer commit.

### Phase L4 — Same-view runtime localization (6–10 weeks)

**Build:**

- Ground-map descriptors and candidate retrieval.
- LiDAR/RGB-D temporal submaps.
- Robust geometric refinement and covariance.
- Fixed-lag SE(2) fusion and integrity modes.

**Acceptance:**

- Runtime localizes on held-out commissioning routes without RTK input.
- It survives specified GNSS dropout lengths.
- Wrong neighboring-tunnel candidates are rejected or retained as ambiguity.
- TF and estimator latency remain within the control/planning budget.

### Phase L5 — Learned aerial/ground bridge (8–16 weeks)

**Build:**

- Versioned pair/negative dataset generator.
- Aerial and robot-BEV encoders.
- Coarse retrieval plus fine SE(2) cost volume.
- Confidence calibration, TensorRT/ONNX export, and shadow-mode evaluation.

**Acceptance:**

- Evaluation uses held-out route/day/condition splits.
- Learned retrieval exceeds deterministic aerial baseline without increasing false-confident matches.
- Fine pose predictions are calibrated by error versus predicted uncertainty.
- Ground-map localization remains the safe primary path.

### Phase L6 — Production hardening and lifecycle (ongoing)

**Build:**

- Multi-hypothesis recovery.
- Map change detection and version rollout/rollback.
- Seasonal data capture and model drift monitoring.
- Replay-CI regression corpus.
- Operator diagnostics and automated event capture.

**Acceptance:**

- A map/model update can be shadowed, promoted, and rolled back.
- All known field failures have deterministic replay tests.
- Behavior responds correctly to every localization mode and protection-level threshold.

---

## 13. Validation strategy

### 13.1 Test pyramid

1. **Unit tests:** SE(2), angle wrapping, covariance projection, geodesy, lever arms, TF inversion, cost-volume decoding.
2. **Property tests:** transform composition/inversion; covariance positive semidefinite; frame/unit invariants.
3. **Synthetic tests:** known shifts/rotations, controlled noise/outliers, repeated patterns, map warp.
4. **Bag replay:** deterministic outputs and latency on golden/failure MCAPs.
5. **Simulation:** GNSS bias/dropout, wheel slip, camera loss, LiDAR degradation, kidnapped robot.
6. **Field validation:** RTK installed only as a non-fused reference on held-out runs.
7. **Seasonal regression:** repeat selected routes after meaningful appearance/map changes.

### 13.2 No label leakage

During final validation, RTK is logged as reference but is not provided to the runtime estimator, candidate generator, or learned network. Validation routes/days are excluded from map alignment, model training, hyperparameter selection, and threshold tuning.

### 13.3 Metrics

Report distributions by environment and mode:

```text
x error, y error, horizontal error
yaw error
cross-track and along-track error
relative repeatability at selected physical transects
ATE/RPE for diagnostic context
protection-level exceedance rate
NIS/NEES consistency where applicable
localization availability
mean/maximum odometry-only duration
relocalization time and distance
false-positive global update count
wrong-hypothesis switch count
TF age, end-to-end latency, CPU/GPU/memory
```

Always show 50th, 95th, 99th percentile, maximum, and sample count. Separate open field, near structures, between rows, tunnel entrance, tunnel interior, roads, and transitions.

### 13.4 Fault-injection matrix

| Fault | Expected detection | Expected response |
|---|---|---|
| GNSS bias/multipath | Innovation and receiver-quality fault | Reject GNSS; retain map/LIO |
| GNSS loss | Age/status fault | Continue bounded LIO/map mode |
| Wheel slip | Wheel/LIO/IMU disagreement | Inflate/drop wheel factor |
| One LiDAR loss | Stream/coverage health | Continue degraded if observability adequate |
| Camera glare/darkness | Image quality/OOD | Drop visual channels; LiDAR path remains |
| Dust/vegetation returns | Residual/class inconsistency | Robust rejection/down-weight |
| Wrong adjacent tunnel | Multi-peak/geometry/temporal inconsistency | `AMBIGUOUS`; no global jump |
| Stale map | Persistent residual/change cluster | Degrade feature/map tile; upload event |
| Time offset | Cross-sensor motion residual | Reject affected source; calibration alert |
| TF unavailable/stale | TF age/lookup failure | Do not publish fabricated pose; safe degradation |

---

## 14. Risks and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Orthomosaic is less accurate than assumed | Systematic global bias that ML cannot remove | Independent map audit; explicit map covariance; ground-map alignment report |
| RTK is used as perfect truth | Noisy/bad labels and misleading metrics | Fixed-only gates, smoothing, covariance weighting, held-out reference runs |
| Single-antenna yaw is mislabeled | Network and map learn wrong orientation | Joint LIO/RTK optimization; course gate; bidirectional runs |
| Cross-view network memorizes site/GNSS prior | High offline score, poor recovery/generalization | Route/day split, hard negatives, blinded prior tests |
| Repeated tunnels/rows alias | Catastrophic discrete pose jump | Cost distributions, multi-hypothesis tracking, entrance/end evidence |
| Seasonal crop change invalidates appearance | Availability loss or false match | Stable-class semantics, LiDAR geometry, seasonal data, map versions |
| Two LIO outputs are naively fused | Overconfident correlated estimate | One local odometry authority; raw/measurement-level fusion or conservative adapter |
| Map match and LIO share data | Underestimated covariance | Keyframing, conservative covariance, empirical consistency tests |
| Calibration drifts after service | Persistent pose bias | Serial-bound manifests, startup checks, scheduled/triggered recalibration |
| Global correction destabilizes control | Path/controller discontinuity | Control in `odom`; global planning in `map`; correction-aware behavior |
| ML inference failure | Localization outage | Deterministic ground geometric baseline and odometry-only mode |
| “Sub-cm” becomes an untestable slogan | Unsafe product expectation | Explicit metrics, percentiles, reference, ODD, and protection levels |

---

## 15. Build, integrate, and research boundaries

### Integrate rather than rebuild

- LIO: FAST-LIO2-class implementation or another validated Livox-compatible package.
- Factor graph: GTSAM/iSAM2.
- Point-cloud registration: Open3D/PCL-style robust ICP/GICP; evaluate TEASER++ for high-outlier initialization where appropriate.
- Geodesy/raster handling: PROJ and GDAL.
- Model serving: ONNX Runtime/TensorRT.
- Logging/replay: rosbag2/MCAP.
- Visualization: Foxglove/RViz/rerun/QGIS.

### Build as JABAS differentiation

- Site commissioning and map-artifact pipeline.
- Aerial/ground dataset generator with uncertainty and hard negatives.
- Agricultural stable-feature ontology.
- Same-view plus cross-view candidate orchestration.
- SE(2) map-match covariance and observability logic.
- Multi-hypothesis agricultural alias handling.
- Integrity/protection-level interface to behavior and safety.
- Seasonal map/model lifecycle and field-debug tooling.

### Research bets kept out of the initial safety path

- End-to-end global pose regression.
- Foundation-model descriptors without calibrated site validation.
- Learned covariance without consistency monitoring.
- Online map rewriting from one robot pass.
- Neural implicit maps as the only localization reference.

---

## 16. Concrete deliverables

A complete first production candidate consists of:

1. Frame/geodesy/TF interface specification.
2. Canonical recording profile and commissioning runbook.
3. Versioned calibration artifacts and reports.
4. Aerial map compiler and map-quality report.
5. RTK/LIO/wheel commissioning optimizer.
6. Versioned commissioned ground-reference map.
7. Deterministic ground-map localizer.
8. Aerial/ground dataset generator.
9. Coarse retrieval and fine SE(2) correlation models.
10. Geometric refinement with directional covariance.
11. Robust fixed-lag planar estimator.
12. Multi-hypothesis relocalization manager.
13. `map → odom` TF publisher and planar pose API.
14. Localization integrity/protection-level monitor.
15. Nav2 behavior integration for degraded/ambiguous/lost modes.
16. Replay, simulation, fault-injection, and held-out RTK validation suite.
17. Map/model/calibration promotion and rollback process.
18. Operator-facing diagnostics and field-event reports.

---

## 17. Decisions required before implementation

Do not freeze detailed thresholds or model sizes until these are answered:

- ROS 2 distribution and deployment OS.
- Robot kinematics, maximum speed/yaw rate, and base-link definition.
- Exact ordinary GNSS and temporary RTK receiver/antenna configuration.
- Whether temporary dual-antenna heading is available.
- Mid-360 and D555 placement, overlap, rates, firmware, and time-sync capability.
- Current LIO implementation, topics, frames, covariance, and health outputs.
- Compute/GPU, thermal envelope, and allowed localization latency.
- Orthomosaic CRS, GSD, acquisition method/date, DSM availability, and survey report.
- Expected route extent and maximum distance/time without observable map features.
- Required absolute, cross-track, repeatability, yaw, availability, and integrity metrics.
- Seasonal ODD and map refresh policy.

---

## 18. Primary references and implementation starting points

- ROS REP-105 coordinate frames: https://reps.openrobotics.org/rep-0105/
- Nav2 transform setup: https://docs.nav2.org/setup_guides/transformation/setup_transforms.html
- FAST-LIO2 implementation: https://github.com/hku-mars/FAST_LIO
- Livox ROS 2 driver: https://github.com/Livox-SDK/livox_ros_driver2
- GTSAM: https://github.com/borglab/gtsam and https://gtsam.org/
- `robot_localization`: https://github.com/cra-ros-pkg/robot_localization
- Scan Context place recognition: https://github.com/irapkaist/scancontext
- TEASER++ robust registration: https://github.com/MIT-SPARK/TEASER-plusplus
- Open3D registration: https://www.open3d.org/docs/latest/tutorial/pipelines/icp_registration.html
- PROJ topocentric coordinates: https://proj.org/en/stable/operations/conversions/topocentric.html
- GDAL geotransforms: https://gdal.org/en/stable/tutorials/geotransforms_tut.html
- Semantic cross-view LiDAR localization: https://arxiv.org/abs/2203.08925 and https://github.com/iandouglas96/cross_view_slam
- BEVLoc cross-view localization: https://arxiv.org/abs/2410.06410
- Dense-flow 3-DoF cross-view localization: https://arxiv.org/abs/2309.15556
- Robust noise models in GTSAM: https://gtsam.org/2019/09/20/robust-noise-model.html

Treat research repositories as design references until their licenses, maintenance, ROS 2 compatibility, runtime, and field performance are independently verified for the product.
