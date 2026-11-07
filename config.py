# ============================================================
#  SHIFT GEARS — TUNING KNOBS
#  Every number that shapes the game lives here.
#  Tweak freely; nothing else needs to change.
# ============================================================

SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

# --- Physics (Verlet truss simulation) ---
GRAVITY = 0.55          # base gravity, px per frame^2
DAMPING = 0.999         # air drag; 1.0 = none
CONSTRAINT_ITERS = 24   # solver passes per frame; more = stiffer, slower

# --- GEARS: the SHIFT theme. The world changes mid-crossing. ---
# gravity multiplies base gravity, friction scales the car's acceleration.
GEARS = [
    {"name": "1st · DRIVE", "gravity": 1.0,  "friction": 1.0,  "color": (80, 200, 120)},
    {"name": "2nd · HEAVY", "gravity": 1.7,  "friction": 1.0,  "color": (240, 200, 80)},
    {"name": "3rd · ICE",   "gravity": 1.0,  "friction": 0.05, "color": (120, 200, 240)},
    {"name": "4th · GALE",  "gravity": 0.55, "friction": 0.3,  "color": (200, 120, 240)},
]
# GALE: low gravity, floaty and bouncy, brakes half-asleep. The car
# goes light on the final stretch — a flat deck matters more than ever.
# Gears shift by DISTANCE, not time: at these fractions of the crossing,
# so every run hits every gear no matter how fast or slow the car is.
# One shift point per gear after the first: len(points) == len(GEARS) - 1.
GEAR_SHIFT_POINTS = (0.25, 0.50, 0.75)

# --- Materials ---
WOOD  = {"name": "Wood",  "max_strain": 0.030, "cost_per_px": 8,  "width": 7, "color": (170, 115, 65)}
STEEL = {"name": "Steel", "max_strain": 0.060, "cost_per_px": 14, "width": 5, "color": (145, 155, 170)}
# Steel survives ~2x the stretch of wood. Same idea as the web prototype.

# --- Building ---
MAX_BEAM_LEN = 190
MIN_BEAM_LEN = 24
SNAP_RADIUS = 18        # px: click near a joint to build from it

# --- Vehicle ---
SUBSTEPS = 3            # physics substeps per frame; more = stabler at high g
CRUISE_SPEED = 2.2      # px/frame the car aims for while its wheels grip
WHEEL_R = 14
TIMEOUT_SECS = 40       # a test that takes longer than this fails
