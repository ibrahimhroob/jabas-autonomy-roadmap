# A coherent, timestamped, versioned snapshot of the world model.
# This is the central contract of the platform (README principle #1):
# perception/localization WRITE it; prediction/planning/monitoring READ it.
#
# Layers may be empty (width==0) if a producer is not yet available; consumers
# must check width/height before indexing.

std_msgs/Header header

uint64 version                       # monotonically increasing snapshot id

GridLayer traversability             # risk in [0,1] + uncertainty (see GridLayer)
GridLayer elevation                  # terrain height + variance
GridLayer semantics                  # per-cell class id + confidence

TrackedObject[] dynamic_objects      # tracked agents with optional predictions

float32 localization_confidence      # [0,1] from the localization integrity monitor (C7/C9)
