# ============================================================
#  SHIFT GEARS — build a bridge, then survive every gear.
#  Build mode: drag to place beams. Test mode: the car drives
#  itself while the world SHIFTs gears under it.
# ============================================================
import math
import pygame

import config as C
from physics import World, Node, collide_circle_seg
from levels import LEVELS

_fonts = {}


def txt(surf, s, x, y, size=22, color=(235, 235, 240), center=False):
    f = _fonts.get(size)
    if f is None:
        f = pygame.font.SysFont(None, size)
        _fonts[size] = f
    img = f.render(s, True, color)
    r = img.get_rect()
    if center:
        r.center = (int(x), int(y))
    else:
        r.topleft = (int(x), int(y))
    surf.blit(img, r)


def stress_color(s):
    s = max(0.0, min(1.0, s))
    if s < 0.5:  # green -> yellow
        t = s / 0.5
        return (int(70 + 170 * t), 200, 90)
    t = (s - 0.5) / 0.5  # yellow -> red
    return (240, int(200 - 130 * t), int(90 - 20 * t))


def beam_cost(a, b, material):
    spec = C.WOOD if material == "wood" else C.STEEL
    return math.hypot(b.x - a.x, b.y - a.y) * spec["cost_per_px"]


class Vehicle:
    def __init__(self, world, x, y):
        self.body = Node(x, y - 26, inv_mass=0.35)
        self.w1 = Node(x - 22, y - C.WHEEL_R, inv_mass=1.0)
        self.w2 = Node(x + 22, y - C.WHEEL_R, inv_mass=1.0)
        for n in (self.body, self.w1, self.w2):
            world.add_node(n)
        self.parts = [self.body, self.w1, self.w2]
        self.links = [
            world.add_beam(self.body, self.w1, unbreakable=True, vehicle=True),
            world.add_beam(self.body, self.w2, unbreakable=True, vehicle=True),
            world.add_beam(self.w1, self.w2, unbreakable=True, vehicle=True),
        ]
        self.grounded = False


class Game:
    def __init__(self, selftest=False):
        pygame.init()
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        pygame.display.set_caption("SHIFT GEARS — Game Off 2026")
        self.clock = pygame.time.Clock()
        self.selftest = selftest

        self.level_idx = 0
        self.material = "wood"
        self.mode = "build"          # build | test | results
        self.drag_from = None        # joint node or raw point while dragging
        self.mouse = (0, 0)

        self.world = None
        self.joints = []             # buildable nodes (anchors + placed)
        self.bridge_beams = []       # player beams (scored + deletable)
        self.vehicle = None
        self.test_t = 0.0
        self.gear_idx = 0
        self.banner_t = 0.0
        self.result = None
        self.gears_seen = 1

        self.load_level(0)

    # ---------------- level setup ----------------
    def load_level(self, idx):
        self.level_idx = idx % len(LEVELS)
        lv = LEVELS[self.level_idx]
        self.world = World()
        self.joints = []
        self.bridge_beams = []
        self.vehicle = None
        self.mode = "build"
        self.result = None
        dy = lv["deck_y"]

        def pin(x, y):
            n = Node(x, y, pinned=True)
            self.world.add_node(n)
            self.joints.append(n)
            return n

        # cliffs
        for ax, ay in lv["anchors"]:
            pin(ax, ay)
        # start + end platforms (unbreakable road)
        s0, s1 = lv["start_platform"]
        e0, e1 = lv["end_platform"]
        for x0, x1 in ((s0, s1), (e0, e1)):
            a, b = pin(x0, dy), pin(x1, dy)
            self.world.add_beam(a, b, material="platform", unbreakable=True)
        self.spawn_x = s0 + 90

    def get_joint(self, x, y):
        for j in self.joints:
            if math.hypot(j.x - x, j.y - y) <= 12:
                return j
        n = Node(x, y)
        self.world.add_node(n)
        self.joints.append(n)
        return n

    def nearest_joint(self, x, y, radius):
        best, bd = None, radius
        for j in self.joints:
            d = math.hypot(j.x - x, j.y - y)
            if d <= bd:
                best, bd = j, d
        return best

    @staticmethod
    def level_btn_x(i):
        # Level buttons sit right-aligned; 40px pitch, 30px wide.
        return C.SCREEN_W - 12 - len(LEVELS) * 40 + i * 40

    @property
    def spent(self):
        return sum(b.cost for b in self.bridge_beams)

    # ---------------- test mode ----------------
    def start_test(self):
        lv = LEVELS[self.level_idx]
        self.vehicle = Vehicle(self.world, self.spawn_x, lv["deck_y"])
        self.mode = "test"
        self.test_t = 0.0
        self.gear_idx = 0
        self.banner_t = 0.0
        self.gears_seen = 1

    def stop_test(self):
        if self.vehicle:
            for n in self.vehicle.parts:
                if n in self.world.nodes:
                    self.world.nodes.remove(n)
            for b in self.vehicle.links:
                self.world.remove_beam(b)
        # broken bridge beams stay broken in build view? No — repair on exit.
        for b in self.bridge_beams:
            b.broken = False
            b.stress = 0.0
        self.vehicle = None
        self.mode = "build"

    def update_test(self, dt):
        lv = LEVELS[self.level_idx]
        self.test_t += dt
        gear = C.GEARS[self.gear_idx]

        # gear shifts by crossing progress (0 = start, 1 = goal)
        v0 = self.vehicle
        progress = (v0.body.x - self.spawn_x) / max(1.0, lv["goal_x"] - self.spawn_x)
        new_gi = 0
        for i, pt in enumerate(C.GEAR_SHIFT_POINTS):
            if progress >= pt:
                new_gi = i + 1
        new_gi = min(len(C.GEARS) - 1, new_gi)
        new_gi = max(self.gear_idx, new_gi)  # gears only shift UP, never back
        if new_gi != self.gear_idx:
            self.gear_idx = new_gi
            self.gears_seen = max(self.gears_seen, new_gi + 1)
            self.banner_t = 1.4
            gear = C.GEARS[self.gear_idx]
        self.banner_t = max(0.0, self.banner_t - dt)

        v = self.vehicle
        v.grounded = False
        # Substeps: integrate + solve + collide in small bites so heavy
        # gravity can never drag a wheel through the deck in one go.
        for _ in range(C.SUBSTEPS):
            self.world.step(gear["gravity"] * C.GRAVITY / C.SUBSTEPS,
                            C.CONSTRAINT_ITERS, C.DAMPING)
            for w in (v.w1, v.w2):
                for bm in self.world.beams:
                    if bm.broken or bm.vehicle:
                        continue
                    if collide_circle_seg(w, bm, C.WHEEL_R):
                        v.grounded = True

        # Engine: throttle is always strong (the car stays capable);
        # brakes are grip-limited, so on ICE downhills the car just
        # keeps accelerating — build flat or catch air.
        if v.grounded:
            for w in (v.w1, v.w2):
                vx = w.x - w.px
                dv = C.CRUISE_SPEED - vx
                gain = 0.08 if dv >= 0 else 0.08 * gear["friction"]
                w.x += dv * gain

        # win / lose
        if v.body.x >= lv["goal_x"]:
            self.finish(True, "crossed the line!")
        elif v.body.y > lv["kill_y"]:
            self.finish(False, "the car took a swim.")
        elif self.test_t > C.TIMEOUT_SECS:
            self.finish(False, "out of time.")

    def finish(self, won, why):
        lv = LEVELS[self.level_idx]
        self.result = {
            "won": won,
            "why": why,
            "gears": self.gears_seen,
            "under_budget": self.spent <= lv["budget"],
        }
        self.mode = "results"

    # ---------------- input ----------------
    def on_mouse_down(self, pos, button):
        if self.mode != "build":
            return
        if button == 1:  # build
            j = self.nearest_joint(*pos, C.SNAP_RADIUS)
            self.drag_from = ("joint", j) if j else ("point", pos)
        elif button == 3:  # delete
            for bm in list(self.bridge_beams):
                if self._near_beam(pos, bm, 9):
                    self.world.remove_beam(bm)
                    self.bridge_beams.remove(bm)
                    # prune orphan joints (not anchors/platforms)
                    for n in (bm.a, bm.b):
                        if n in self.joints and n.pinned is False:
                            used = any(n in (x.a, x.b) for x in self.world.beams)
                            if not used:
                                self.joints.remove(n)
                                self.world.nodes.remove(n)
                    break

    def on_mouse_up(self, pos):
        if self.mode != "build" or self.drag_from is None:
            self.drag_from = None
            return
        kind, val = self.drag_from
        j1 = val if kind == "joint" else self.get_joint(*val)
        j2 = self.nearest_joint(*pos, C.SNAP_RADIUS) or self.get_joint(*pos)
        self.drag_from = None
        if j1 is j2:
            return
        dist = math.hypot(j2.x - j1.x, j2.y - j1.y)
        if not (C.MIN_BEAM_LEN <= dist <= C.MAX_BEAM_LEN):
            return
        if any({b.a, b.b} == {j1, j2} for b in self.world.beams):
            return
        spec = C.WOOD if self.material == "wood" else C.STEEL
        bm = self.world.add_beam(j1, j2, material=self.material,
                                 max_strain=spec["max_strain"],
                                 cost=beam_cost(j1, j2, self.material))
        self.bridge_beams.append(bm)

    @staticmethod
    def _near_beam(pos, bm, tol):
        px, py = pos
        ax, ay, bx, by = bm.a.x, bm.a.y, bm.b.x, bm.b.y
        abx, aby = bx - ax, by - ay
        l2 = abx * abx + aby * aby or 1e-9
        t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / l2))
        return math.hypot(px - (ax + abx * t), py - (ay + aby * t)) <= tol

    def on_key(self, key):
        if key == pygame.K_1:
            self.material = "wood"
        elif key == pygame.K_2:
            self.material = "steel"
        elif key == pygame.K_SPACE and self.mode == "build":
            self.start_test()
        elif key == pygame.K_ESCAPE and self.mode in ("test", "results"):
            self.stop_test()
        elif key == pygame.K_r:
            if self.mode in ("test", "results"):
                self.stop_test()
                self.start_test()
            elif self.mode == "build":  # clear the bridge
                for bm in list(self.bridge_beams):
                    self.world.remove_beam(bm)
                self.bridge_beams = []
                self.load_level(self.level_idx)
        elif key == pygame.K_n and self.mode in ("build", "results"):
            self.load_level(self.level_idx + 1)

    # ---------------- drawing ----------------
    def draw(self):
        s = self.screen
        s.fill((16, 20, 32))
        lv = LEVELS[self.level_idx]
        dy = lv["deck_y"]

        # cliffs
        pygame.draw.rect(s, (38, 44, 60), (0, dy, 220, C.SCREEN_H - dy))
        pygame.draw.rect(s, (38, 44, 60), (1060, dy, C.SCREEN_W - 1060, C.SCREEN_H - dy))
        pygame.draw.rect(s, (30, 150, 200), (0, lv["kill_y"], C.SCREEN_W, C.SCREEN_H - lv["kill_y"]))

        # goal flag
        pygame.draw.line(s, (240, 240, 240), (lv["goal_x"], dy - 70), (lv["goal_x"], dy), 3)
        pygame.draw.polygon(s, (240, 200, 80),
                            [(lv["goal_x"], dy - 70), (lv["goal_x"] + 34, dy - 58), (lv["goal_x"], dy - 46)])

        for bm in self.world.beams:
            if bm.broken or bm.vehicle:
                continue
            if bm.material == "platform":
                color, width = (90, 95, 115), 8
            else:
                spec = C.WOOD if bm.material == "wood" else C.STEEL
                color = stress_color(bm.stress)
                width = spec["width"]
            pygame.draw.line(s, color, (bm.a.x, bm.a.y), (bm.b.x, bm.b.y), width)

        if self.mode == "build":
            for j in self.joints:
                if j.pinned:
                    pygame.draw.circle(s, (200, 200, 210), (int(j.x), int(j.y)), 6)
                else:
                    pygame.draw.circle(s, (150, 160, 190), (int(j.x), int(j.y)), 4)
            self.draw_drag()
            self.draw_build_hud()
        else:
            self.draw_vehicle()
            self.draw_test_hud()

        if self.mode == "results":
            self.draw_results()

        pygame.display.flip()

    def draw_drag(self):
        if not self.drag_from:
            return
        kind, val = self.drag_from
        x0, y0 = (val.x, val.y) if kind == "joint" else val
        x1, y1 = self.mouse
        dist = math.hypot(x1 - x0, y1 - y0)
        ok = C.MIN_BEAM_LEN <= dist <= C.MAX_BEAM_LEN
        pygame.draw.line(self.screen, (120, 220, 140) if ok else (230, 90, 90),
                         (x0, y0), (x1, y1), 4)
        # max-length ring
        pygame.draw.circle(self.screen, (120, 120, 140), (int(x0), int(y0)),
                           C.MAX_BEAM_LEN, 1)
        txt(self.screen, f"{int(dist)} / {C.MAX_BEAM_LEN}", x1 + 12, y1 - 10,
            20, (235, 235, 240) if ok else (255, 120, 120))

    def draw_build_hud(self):
        lv = LEVELS[self.level_idx]
        pygame.draw.rect(self.screen, (10, 12, 20), (0, 0, C.SCREEN_W, 44))
        txt(self.screen, f"Level {self.level_idx + 1}: {lv['name']}", 12, 12, 24)
        over = self.spent > lv["budget"]
        txt(self.screen, f"${int(self.spent)} / ${lv['budget']}",
            330, 12, 24, (255, 120, 120) if over else (235, 235, 240))
        mat = "Wood [1]" if self.material == "wood" else "Steel [2]"
        txt(self.screen, mat, 560, 12, 24, (170, 200, 255))
        for i in range(len(LEVELS)):
            x = self.level_btn_x(i)
            c = (90, 200, 130) if i == self.level_idx else (70, 75, 95)
            pygame.draw.rect(self.screen, c, (x, 8, 30, 28), border_radius=6)
            txt(self.screen, str(i + 1), x + 10, 12, 22)
        txt(self.screen, "Drag: build · Right-click: delete · Space: test · 1/2: material · R: clear",
            12, C.SCREEN_H - 28, 20, (140, 145, 160))

    def draw_vehicle(self):
        v = self.vehicle
        if not v:
            return
        for b in v.links:
            pygame.draw.line(self.screen, (60, 65, 80),
                             (b.a.x, b.a.y), (b.b.x, b.b.y), 4)
        for w in (v.w1, v.w2):
            pygame.draw.circle(self.screen, (25, 25, 30), (int(w.x), int(w.y)), C.WHEEL_R)
            pygame.draw.circle(self.screen, (150, 155, 170), (int(w.x), int(w.y)), C.WHEEL_R, 3)
        bx, by = v.body.x, v.body.y
        pygame.draw.polygon(self.screen, (200, 70, 70),
                            [(bx - 30, by + 12), (bx - 30, by - 6),
                             (bx - 12, by - 20), (bx + 14, by - 20),
                             (bx + 30, by - 2), (bx + 30, by + 12)])

    def draw_test_hud(self):
        pygame.draw.rect(self.screen, (10, 12, 20), (0, 0, C.SCREEN_W, 44))
        txt(self.screen, f"TEST — {LEVELS[self.level_idx]['name']}", 12, 12, 24)
        # Gear chips sized to fit however many gears exist.
        w, gap = 114, 8
        x0 = C.SCREEN_W - len(C.GEARS) * (w + gap) - 12
        for i, g in enumerate(C.GEARS):
            x = x0 + i * (w + gap)
            active = i == self.gear_idx
            col = g["color"] if active else (60, 65, 80)
            pygame.draw.rect(self.screen, col, (x, 8, w, 28), border_radius=6,
                             width=0 if active else 2)
            txt(self.screen, g["name"], x + 8, 13, 19,
                (10, 12, 20) if active else (150, 155, 170))
        if self.banner_t > 0:
            txt(self.screen, "SHIFT!", C.SCREEN_W // 2, 120, 90, (255, 220, 100), center=True)

    def draw_results(self):
        s = self.screen
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((5, 8, 16, 200))
        s.blit(overlay, (0, 0))
        r = self.result
        lv = LEVELS[self.level_idx]
        cx = C.SCREEN_W // 2
        txt(s, "✅ CROSSED!" if r["won"] else "❌ WRECKED", cx, 200, 64,
            (110, 230, 140) if r["won"] else (240, 110, 110), center=True)
        txt(s, r["why"], cx, 260, 28, (200, 205, 220), center=True)
        txt(s, f"Gears survived: {r['gears']} / {len(C.GEARS)}", cx, 320, 28, center=True)
        txt(s, f"Budget: ${int(self.spent)} / ${lv['budget']}"
               + ("  ⭐ under budget!" if r["under_budget"] else ""), cx, 360, 28, center=True)
        txt(s, "R: retry · Esc: rebuild · N: next level", cx, 440, 24,
            (140, 145, 160), center=True)

    # ---------------- main loop ----------------
    def run(self):
        if self.selftest:
            return self.run_selftest()
        running = True
        while running:
            dt = self.clock.tick(C.FPS) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.MOUSEMOTION:
                    self.mouse = e.pos
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    if self.mode == "build" and e.pos[1] > 44:
                        handled = False
                        for i in range(len(LEVELS)):
                            x = self.level_btn_x(i)
                            if x <= e.pos[0] <= x + 30 and 8 <= e.pos[1] <= 36:
                                self.load_level(i)
                                handled = True
                        if not handled:
                            self.on_mouse_down(e.pos, e.button)
                    else:
                        self.on_mouse_down(e.pos, e.button)
                elif e.type == pygame.MOUSEBUTTONUP:
                    self.on_mouse_up(e.pos)
                elif e.type == pygame.KEYDOWN:
                    self.on_key(e.key)
            if self.mode == "test":
                self.update_test(dt)
            self.draw()
        pygame.quit()

    def run_selftest(self):
        """Headless playthrough: auto-build a wood truss, run the test.
        --selftest-all plays every level in turn."""
        import sys
        idxs = range(len(LEVELS)) if "--selftest-all" in sys.argv else [self.level_idx]
        all_won = True
        for idx in idxs:
            self.load_level(idx)
            all_won = self._selftest_level() and all_won
        pygame.quit()
        return all_won

    def _selftest_level(self):
        lv = LEVELS[self.level_idx]
        dy = lv["deck_y"]
        s1 = lv["start_platform"][1]
        e0 = lv["end_platform"][0]
        xs = [s1]
        x = s1
        while x < e0:
            x = min(x + 170, e0)
            xs.append(x)

        def wood(a, b):
            bm = self.world.add_beam(a, b, material="wood",
                                     max_strain=C.WOOD["max_strain"],
                                     cost=beam_cost(a, b, "wood"))
            self.bridge_beams.append(bm)

        joints = [self.get_joint(px, dy) for px in xs]
        for a, b in zip(joints, joints[1:]):
            wood(a, b)                       # deck
            mid = self.get_joint((a.x + b.x) / 2, dy + 70)
            wood(a, mid)                     # truss triangle
            wood(mid, b)
        # tie the truss ends down to the cliff anchors
        for ax, ay in lv["anchors"]:
            anc = self.nearest_joint(ax, ay, 4) or self.get_joint(ax, ay)
            end = joints[0] if ax < 640 else joints[-1]
            if math.hypot(end.x - ax, end.y - ay) <= C.MAX_BEAM_LEN:
                wood(anc, end)
        self.start_test()
        frames = 0
        while self.mode != "results" and frames < 3600:
            self.update_test(1.0 / 60.0)
            frames += 1
        r = self.result or {}
        print(f"SELFTEST level={self.level_idx + 1} {lv['name']} mode={self.mode} "
              f"frames={frames} won={r.get('won')} gears={r.get('gears')} why={r.get('why')}")
        return r.get("won", False)


def main():
    import sys
    Game(selftest=("--selftest" in sys.argv or "--selftest-all" in sys.argv)).run()


if __name__ == "__main__":
    main()
