# SHIFT GEARS 🏗️🚗💨

A Game Off 2026 entry (theme: **SHIFT**). Build a bridge, then watch a car
drive across while the world **shifts gears** under it:

- **1st · DRIVE** — normal gravity, full grip
- **2nd · HEAVY** — 1.7× gravity, everything strains
- **3rd · ICE** — nearly zero friction, the car slides

Your bridge has to survive all three. Beat the budget for a bonus ⭐.

## Run it

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

## Controls

| Input | Does |
|---|---|
| Drag mouse | Place a beam between joints |
| Right-click a beam | Delete it (refunded) |
| `1` / `2` | Wood / Steel |
| `Space` | Test drive |
| `R` | Retry test / clear bridge |
| `Esc` | Back to build mode |
| `N` | Next level |

## Make it yours (the 2-minute guide)

- **Tweak the feel** → `config.py`. Every knob is labeled: gravity per
  gear, shift timing, material strength/cost, max beam length, car speed.
- **Add a level** → copy a dict in `levels.py`. Set the gap (`deck_y`,
  platform spans), the `budget`, and a few `anchors` on the cliffs.
- **Add a gear** → append to `GEARS` in `config.py`. Name, gravity,
  friction, color. The HUD and shifting logic pick it up automatically.

## How it works (30 seconds)

Bridges are a truss of nodes + beams simulated with Verlet integration
(`physics.py`): each frame, gravity moves the nodes, then beams pull
their endpoints back to their rest length. A beam measures how far it
stretched *before* being corrected — past its material's limit, it snaps.
The car is just heavier nodes joined by unbreakable beams, with wheels
that collide against the tops of your beams.
