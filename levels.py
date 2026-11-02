# ============================================================
#  LEVELS — add your own by copying one of these dicts.
#  deck_y: height of the road. kill_y: below this = wrecked.
#  goal_x: drive past this x to win. anchors: pinned cliff nodes.
#  The start/end platforms are built automatically.
# ============================================================

LEVELS = [
    {
        "name": "First Shift",
        "budget": 20000,
        "deck_y": 420,
        "start_platform": (20, 200),     # (x0, x1) of the left road
        "end_platform": (1080, 1260),    # (x0, x1) of the right road
        "anchors": [(200, 500), (200, 580), (1080, 500), (1080, 580)],
        "kill_y": 700,
        "goal_x": 1130,
    },
    {
        "name": "Heavy Haul",
        "budget": 18000,
        "deck_y": 430,
        "start_platform": (20, 160),
        "end_platform": (1120, 1260),
        "anchors": [(160, 510), (160, 590), (1120, 510), (1120, 590)],
        "kill_y": 700,
        "goal_x": 1170,
    },
    {
        "name": "Black Ice",
        "budget": 16000,
        "deck_y": 440,
        "start_platform": (20, 140),
        "end_platform": (1140, 1260),
        "anchors": [(140, 520), (140, 600), (1140, 520), (1140, 600)],
        "kill_y": 700,
        "goal_x": 1190,
    },
]
