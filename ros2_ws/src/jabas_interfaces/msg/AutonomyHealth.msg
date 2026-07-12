# Aggregated autonomy health state (C9). Consumed by the behavior layer for
# graceful degradation and by the data engine for event triggering.

std_msgs/Header header

# Overall health level.
uint8 LEVEL_OK=0
uint8 LEVEL_DEGRADED=1
uint8 LEVEL_CRITICAL=2
uint8 level

# Per-subsystem confidences in [0, 1] (1 = healthy).
float32 localization_confidence
float32 perception_confidence
float32 planner_feasibility

# Comms round-trip time to cloud/operator in milliseconds (-1 if unknown).
float32 comms_rtt_ms

# Human-readable active warnings, e.g. "GNSS_RTK_LOST", "HIGH_LOCALIZATION_COVARIANCE".
string[] active_warnings

# Speed cap recommended by the health->speed policy (m/s). Behavior layer must respect.
float32 recommended_max_speed
