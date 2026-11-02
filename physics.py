# ============================================================
#  Verlet truss physics: nodes + beams, solved as constraints.
#  Beams measure their own stretch each frame and snap past
#  their material's limit. Simple, stable, and fast enough.
# ============================================================
import math


class Node:
    __slots__ = ("x", "y", "px", "py", "inv_mass", "pinned")

    def __init__(self, x, y, inv_mass=1.0, pinned=False):
        self.x = float(x)
        self.y = float(y)
        self.px = float(x)
        self.py = float(y)
        self.pinned = pinned
        self.inv_mass = 0.0 if pinned else float(inv_mass)


class Beam:
    __slots__ = ("a", "b", "rest", "material", "max_strain",
                 "stress", "broken", "cost", "unbreakable", "vehicle")

    def __init__(self, a, b, material="wood", max_strain=0.03,
                 cost=0.0, unbreakable=False, vehicle=False):
        self.a = a
        self.b = b
        self.rest = math.hypot(b.x - a.x, b.y - a.y) or 1e-6
        self.material = material
        self.max_strain = max_strain
        self.stress = 0.0          # 0 = slack, 1 = snapping
        self.broken = False
        self.cost = cost
        self.unbreakable = unbreakable
        self.vehicle = vehicle     # car parts: skipped by wheel collision


class World:
    def __init__(self):
        self.nodes = []
        self.beams = []

    def add_node(self, node):
        self.nodes.append(node)
        return node

    def add_beam(self, a, b, material="wood", max_strain=0.03,
                 cost=0.0, unbreakable=False, vehicle=False):
        bm = Beam(a, b, material, max_strain, cost, unbreakable, vehicle)
        self.beams.append(bm)
        return bm

    def remove_beam(self, bm):
        if bm in self.beams:
            self.beams.remove(bm)

    # ---- one simulation step ----
    def step(self, gravity, iterations, damping):
        # 1) integrate
        for n in self.nodes:
            if n.pinned:
                continue
            vx = (n.x - n.px) * damping
            vy = (n.y - n.py) * damping
            n.px, n.py = n.x, n.y
            n.x += vx
            n.y += vy + gravity

        # 2) measure strain BEFORE solving (solving erases it)
        for bm in self.beams:
            if bm.broken or bm.unbreakable:
                continue
            dx = bm.b.x - bm.a.x
            dy = bm.b.y - bm.a.y
            dist = math.hypot(dx, dy) or 1e-9
            strain = abs(dist - bm.rest) / bm.rest
            target = strain / bm.max_strain
            bm.stress = max(bm.stress * 0.92, target)
            if bm.stress >= 1.0:
                bm.broken = True

        # 3) solve distance constraints
        for _ in range(iterations):
            for bm in self.beams:
                if bm.broken:
                    continue
                a, b = bm.a, bm.b
                dx = b.x - a.x
                dy = b.y - a.y
                dist = math.hypot(dx, dy) or 1e-9
                w1, w2 = a.inv_mass, b.inv_mass
                wsum = w1 + w2
                if wsum == 0.0:
                    continue
                diff = (dist - bm.rest) / dist / wsum
                a.x += dx * diff * w1
                a.y += dy * diff * w1
                b.x -= dx * diff * w2
                b.y -= dy * diff * w2


def collide_circle_seg(node, beam, radius):
    """Push a wheel node out of a beam segment. Only the TOP side counts,
    so the car rides on decks instead of snagging under them."""
    ax, ay = beam.a.x, beam.a.y
    bx, by = beam.b.x, beam.b.y
    abx, aby = bx - ax, by - ay
    len2 = abx * abx + aby * aby or 1e-9
    t = max(0.0, min(1.0, ((node.x - ax) * abx + (node.y - ay) * aby) / len2))
    cx, cy = ax + abx * t, ay + aby * t
    dx, dy = node.x - cx, node.y - cy
    dist = math.hypot(dx, dy) or 1e-9
    if dist >= radius:
        return False
    nx, ny = dx / dist, dy / dist
    if ny > -0.35:          # hit from below or the side: ignore
        return False
    push = radius - dist
    node.x += nx * push
    node.y += ny * push
    return True
