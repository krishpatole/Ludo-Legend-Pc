"""Shared maths + drawing helpers. Expensive surfaces are cached."""
from __future__ import annotations
import math
from functools import lru_cache
import pygame
from config.settings import WIDTH, HEIGHT

import os, sys


def resource_path(*parts: str) -> str:
    """Path to a bundled asset; works from source and from a PyInstaller .exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


FONT_NAMES = "segoeui,helveticaneue,arial,dejavusans,liberationsans,verdana"
_fonts: dict = {}
_text_cache: dict = {}


def font(size: int, bold: bool = True) -> pygame.font.Font:
    k = (size, bold)
    if k not in _fonts:
        _fonts[k] = pygame.font.SysFont(FONT_NAMES, size, bold=bold)
    return _fonts[k]


def text_surf(text, size, color, bold=True):
    k = (text, size, tuple(color), bold)
    s = _text_cache.get(k)
    if s is None:
        if len(_text_cache) > 700:
            _text_cache.clear()
        s = font(size, bold).render(text, True, color)
        _text_cache[k] = s
    return s


def draw_text(surf, text, size, color, pos, anchor="center", bold=True, shadow=None, alpha=255):
    s = text_surf(text, size, color, bold)
    if alpha < 255:
        s = s.copy()
        s.set_alpha(int(alpha))
    r = s.get_rect(**{anchor: pos})
    if shadow:
        sh = text_surf(text, size, shadow, bold)
        if alpha < 255:
            sh = sh.copy(); sh.set_alpha(int(alpha))
        surf.blit(sh, r.move(2, 2))
    surf.blit(s, r)
    return r


@lru_cache(maxsize=512)
def fit_text(text: str, size: int, max_w: int, bold: bool = True, min_size: int = 9):
    """Shrink the font until `text` fits in `max_w` pixels; if it still does not at `min_size`,
    cut it and add '...'. Returns (text_to_draw, font_size). Used for every player name."""
    s = size
    while s > min_size and font(s, bold).size(text)[0] > max_w:
        s -= 1
    if font(s, bold).size(text)[0] > max_w:
        t = text
        while len(t) > 1 and font(s, bold).size(t + "...")[0] > max_w:
            t = t[:-1]
        text = t.rstrip() + "..."
    return text, s


def draw_text_fit(surf, text, size, color, pos, max_w, anchor="center", bold=True, shadow=None, alpha=255, min_size=9):
    text, s = fit_text(text, int(size), int(max_w), bold, min_size)
    return draw_text(surf, text, s, color, pos, anchor, bold, shadow, alpha)


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(a, b, t):
    return tuple(int(lerp(a[i], b[i], t)) for i in range(3))


def shade(c, f):
    return tuple(int(clamp(v * f, 0, 255)) for v in c[:3])


def approach(cur, target, speed, dt):
    """Frame-rate independent exponential smoothing."""
    return cur + (target - cur) * (1 - math.exp(-speed * dt))


def ease_out_cubic(t):
    t = clamp(t); return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp(t); return t * t * (3 - 2 * t)


def ease_out_back(t):
    t = clamp(t); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


@lru_cache(maxsize=64)
def rounded_mask(w, h, r):
    m = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(m, (255, 255, 255, 255), (0, 0, w, h), border_radius=r)
    return m


@lru_cache(maxsize=128)
def gradient_surface(w, h, top, bottom, radius=0):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        pygame.draw.line(s, lerp_color(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
    if radius:
        s.blit(rounded_mask(w, h, radius), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return s


@lru_cache(maxsize=256)
def _glow(radius, color, q):
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        a = int(255 * (q / 10) * (1 - r / radius) ** 2)
        pygame.draw.circle(s, (*color, min(255, a)), (radius, radius), r)
    return s


def draw_glow(surf, center, radius, color, strength=1.0):
    q = int(clamp(strength, 0, 1) * 10)
    if q <= 0 or radius < 2:
        return
    g = _glow(int(radius), tuple(color), q)
    surf.blit(g, g.get_rect(center=(int(center[0]), int(center[1]))))


def draw_rrect(surf, rect, color, radius=10, width=0):
    rect = pygame.Rect(rect)
    if len(color) == 4 and color[3] < 255:
        tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(tmp, color, tmp.get_rect(), width, border_radius=radius)
        surf.blit(tmp, rect.topleft)
    else:
        pygame.draw.rect(surf, color[:3], rect, width, border_radius=radius)


def star_points(cx, cy, r_out, r_in, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / n
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


_PIPS = {1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)],
         4: [(0, 0), (2, 0), (0, 2), (2, 2)], 5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)],
         6: [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (2, 2)]}


def draw_pips(surf, rect, value, color=(30, 30, 50)):
    rect = pygame.Rect(rect)
    pad = rect.w * 0.24
    step = (rect.w - pad * 2) / 2
    r = max(2, int(rect.w * 0.085))
    for cx, cy in _PIPS[value]:
        pygame.draw.circle(surf, color, (int(rect.x + pad + cx * step), int(rect.y + pad + cy * step)), r)


@lru_cache(maxsize=32)
def crown_surface(w, color=(255, 214, 90)):
    h = int(w * 0.75)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    dark = shade(color, 0.6)
    pts = [(w * .08, h * .85), (w * .02, h * .25), (w * .27, h * .55), (w * .5, h * .08),
           (w * .73, h * .55), (w * .98, h * .25), (w * .92, h * .85)]
    pygame.draw.polygon(s, dark, [(x, y + 3) for x, y in pts])
    pygame.draw.polygon(s, color, pts)
    pygame.draw.rect(s, shade(color, 0.85), (w * .08, h * .72, w * .84, h * .2), border_radius=4)
    for x, y in ((.02, .25), (.5, .08), (.98, .25)):
        pygame.draw.circle(s, (255, 245, 200), (w * x, h * y), max(3, w * .055))
    for x, c in ((.3, (220, 70, 80)), (.5, (80, 200, 255)), (.7, (90, 220, 130))):
        pygame.draw.circle(s, c, (w * x, h * .82), max(2, w * .035))
    return s


@lru_cache(maxsize=32)
def gradient_text(text, size, top, bottom):
    base = font(size, True).render(text, True, (255, 255, 255))
    grad = gradient_surface(base.get_width(), base.get_height(), top, bottom)
    out = base.copy()
    out.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


_bg = None


def get_background():
    global _bg
    if _bg is None:
        _bg = gradient_surface(WIDTH, HEIGHT, (34, 30, 66), (10, 12, 28)).copy()
        for (x, y, r, c) in ((200, 120, 420, (90, 60, 160)), (1180, 640, 460, (40, 90, 170)),
                             (700, 380, 520, (60, 50, 120))):
            g = _glow(r, c, 3)
            _bg.blit(g, g.get_rect(center=(x, y)))
        for gx in range(0, WIDTH, 64):
            for gy in range(0, HEIGHT, 64):
                pygame.draw.circle(_bg, (255, 255, 255, 14), (gx + 32, gy + 32), 1)
    return _bg
