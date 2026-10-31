"""Visual dice: rounded die with pips, shake + spin while rolling, glow when clickable."""
from __future__ import annotations
import math, random
from functools import lru_cache
import pygame
from config.settings import GOLD, GOLD_LIGHT
from utils.helpers import draw_pips, draw_glow, approach, shade, draw_text, gradient_surface, lerp


@lru_cache(maxsize=16)
def die_face(value: int, size: int) -> pygame.Surface:
    S = size + 16
    s = pygame.Surface((S, S), pygame.SRCALPHA)
    r = pygame.Rect(8, 8, size, size)
    rad = size // 5
    pygame.draw.rect(s, (0, 0, 0, 70), r.move(0, 5), border_radius=rad)
    pygame.draw.rect(s, (176, 170, 196), r.move(0, 3), border_radius=rad)
    s.blit(gradient_surface(size, size, (255, 255, 255), (222, 218, 240), rad), r.topleft)
    pygame.draw.rect(s, (255, 255, 255), r.inflate(-8, -8), 1, border_radius=rad - 3)
    pygame.draw.rect(s, GOLD, r, 3, border_radius=rad)
    if value:
        inner = r.inflate(-4, -4)
        draw_pips(s, inner, value, (36, 30, 70))
    else:                                    # never rolled yet: show the crown emblem
        from utils.helpers import crown_surface
        c = crown_surface(int(size * .6))
        s.blit(c, c.get_rect(center=r.center))
    return s


class DiceView:
    def __init__(self, center, size=76):
        self.center, self.size = center, size
        self.value = 0
        self.rolling = False
        self.t = 0.0
        self.dur = 0.9
        self.final = 1
        self._face_t = 0.0
        self.hover = 0.0
        self.settle = 0.0

    @property
    def rect(self):
        r = pygame.Rect(0, 0, self.size + 16, self.size + 16)
        r.center = self.center
        return r

    def start_roll(self, final, duration=0.9):
        self.rolling, self.t, self.dur, self.final = True, 0.0, duration, final
        self.value = random.randint(1, 6)

    def update(self, dt, mouse, enabled) -> bool:
        """Returns True the frame the roll finishes."""
        self.hover = approach(self.hover, 1.0 if (enabled and self.rect.collidepoint(mouse)) else 0.0, 14, dt)
        self.settle = max(0.0, self.settle - dt)
        if not self.rolling:
            return False
        self.t += dt
        self._face_t -= dt
        if self._face_t <= 0:
            self._face_t = 0.05 + 0.1 * (self.t / self.dur)      # faces change more slowly as it settles
            self.value = random.randint(1, 6)
        if self.t >= self.dur:
            self.rolling, self.value, self.settle = False, self.final, 0.35
            return True
        return False

    def draw(self, surf, enabled: bool, t: float, accent):
        cx, cy = self.center
        k = self.t / self.dur if self.rolling else 1.0
        ang = off_x = off_y = 0.0
        scale = 1 + .06 * self.hover
        if self.rolling:
            amp = (1 - k) ** .7
            ang = math.sin(self.t * 38) * 24 * amp + math.sin(self.t * 17) * 40 * amp
            off_x, off_y = math.sin(self.t * 47) * 9 * amp, abs(math.sin(self.t * 21)) * -16 * amp
            scale += .1 * amp
        elif self.settle > 0:
            scale += .12 * math.sin(self.settle / .35 * math.pi)
        if enabled:
            draw_glow(surf, (cx, cy), self.size, accent, .35 + .15 * math.sin(t * 4) + .2 * self.hover)
        img = die_face(self.value, self.size)
        if ang or scale != 1:
            img = pygame.transform.rotozoom(img, ang, scale)
        if not enabled and not self.rolling:
            img = img.copy()
            img.set_alpha(150)
        surf.blit(img, img.get_rect(center=(cx + off_x, cy + off_y)))
        if enabled:
            a = 200 + 55 * math.sin(t * 5)
            draw_text(surf, "ROLL", 15, GOLD_LIGHT, (cx, cy + self.size / 2 + 22), alpha=a, shadow=(0, 0, 0))

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)
