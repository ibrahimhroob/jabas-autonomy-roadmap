# A single tracked dynamic agent in the world model's dynamic layer.

builtin_interfaces/Time stamp

uint32 id                                    # persistent track id
string classification                        # "person" | "animal" | "vehicle" | "robot" | "unknown"
float32 confidence                           # [0, 1]

geometry_msgs/PoseWithCovariance pose        # in the world frame
geometry_msgs/TwistWithCovariance twist      # linear/angular velocity

# Simple predicted future positions (one per prediction step).
# Populated by the prediction module (C4). Empty if no prediction available.
geometry_msgs/Point[] predicted_path
float32 prediction_dt                        # seconds between predicted_path points
