# A single 2D grid layer with per-cell value and (optional) uncertainty.
# Row-major storage: index = row * width + col.
# This is the primitive that the world model exposes for traversability,
# elevation, semantics, and experience layers.

std_msgs/Header header

float32 resolution              # meters per cell
uint32 width                    # number of cells in x
uint32 height                   # number of cells in y
geometry_msgs/Pose origin       # pose of cell (0,0) lower-left, in header.frame_id

# Meaning of `values` depends on the layer:
#   traversability: risk in [0, 1]   (0 = freely drivable, 1 = impassable)
#   elevation:      height in meters
#   semantics:      class id as float (cast to int)
float32[] values

# Per-cell uncertainty (e.g. variance or 1-confidence). May be empty if unknown.
float32[] uncertainty
