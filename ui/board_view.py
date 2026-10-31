"""Static board rendering (cached) + token sprite."""
from __future__ import annotations
import math
from functools import lru_cache
import pygame
from config.settings import CELL, BOARD_SIZE, PLAYER_COLORS, GOLD, GOLD_LIGHT, GOLD_DARK
from game.board import RING, LANES, YARD_ORIGIN, SAFE_RING, START_OFFSET, yard_slot
from utils.helpers import (shade, lerp_color, gradient_surface, star_points, crown_surface, draw_text,
                           font, draw_glow)

MARGIN = 26           # extra pixels around the board for frame + shadow
_cache: dict[frozenset, pygame.Surface] = {}


def _cell(c, r):
    return pygame.Rect(MARGIN + c * CELL, MARGIN + r * CELL, CELL, CELL)


def _board_px(gx, gy):
    return MARGIN + gx * CELL, MARGIN + gy * CELL


def _render(active: frozenset) -> pygame.Surface:
    S = BOARD_SIZE + MARGIN * 2
    s = pygame.Surface((S, S), pygame.SRCALPHA)
    frame = pygame.Rect(MARGIN - 10, MARGIN - 10, BOARD_SIZE + 20, BOARD_SIZE + 20)
    for i in range(10):                                           # soft drop shadow
        pygame.draw.rect(s, (0, 0, 0, 18), frame.inflate(i * 2, i * 2).move(0, 6), border_radius=26 + i)
    s.blit(gradient_surface(frame.w, frame.h, (92, 66, 140), (40, 28, 78), 24), frame.topleft)
    pygame.draw.rect(s, GOLD, frame, 3, border_radius=24)
    pygame.draw.rect(s, GOLD_DARK, frame.inflate(-10, -10), 1, border_radius=20)
    plate = pygame.Rect(MARGIN - 3, MARGIN - 3, BOARD_SIZE + 6, BOARD_SIZE + 6)
    pygame.draw.rect(s, (250, 246, 236), plate, border_radius=14)

    # --- yards ---------------------------------------------------------
    for i, (ox, oy) in enumerate(YARD_ORIGIN):
        is_active = i in active
        base = PLAYER_COLORS[i] if is_active else (132, 132, 148)
        r = pygame.Rect(MARGIN + ox * CELL, MARGIN + oy * CELL, 6 * CELL, 6 * CELL)
        s.blit(gradient_surface(r.w, r.h, shade(base, 1.08), shade(base, .82), 12), r.topleft)
        pygame.draw.rect(s, shade(base, .6), r, 2, border_radius=12)
        inner = r.inflate(-CELL * 1.2, -CELL * 1.2)
        pygame.draw.rect(s, lerp_color(base, (255, 255, 255), .78), inner, border_radius=16)
        pygame.draw.rect(s, shade(base, .7), inner, 2, border_radius=16)
        for sl in range(4):
            gx, gy = yard_slot(i, sl)
            px, py = _board_px(gx, gy)
            pygame.draw.circle(s, shade(base, .78), (px, py), 14)
            pygame.draw.circle(s, lerp_color(base, (255, 255, 255), .5), (px, py), 12)
            pygame.draw.circle(s, shade(base, .88), (px, py + 1), 10)

    # --- path cells ------------------------------------------------------
    coloured = {}
    for pi in range(4):
        for cell in LANES[pi]:
            coloured[cell] = pi
        coloured[RING[START_OFFSET[pi]]] = pi
    ring_idx = {c: i for i, c in enumerate(RING)}
    lane_cells = {c for l in LANES for c in l}
    for r_ in range(15):
        for c_ in range(15):
            in_yard = (c_ < 6 or c_ > 8) and (r_ < 6 or r_ > 8)
            in_ctr = 6 <= c_ <= 8 and 6 <= r_ <= 8
            if in_yard or in_ctr:
                continue
            rect = _cell(c_, r_).inflate(-2, -2)
            if (c_, r_) in coloured:
                pi = coloured[(c_, r_)]
                col = PLAYER_COLORS[pi] if pi in active else (170, 170, 182)
                pygame.draw.rect(s, shade(col, .72), rect.move(0, 1), border_radius=5)
                pygame.draw.rect(s, col, rect, border_radius=5)
                pygame.draw.rect(s, lerp_color(col, (255, 255, 255), .35), rect.inflate(-8, -8), border_radius=3)
                pygame.draw.rect(s, shade(col, .85), rect, 1, border_radius=5)
            else:
                pygame.draw.rect(s, (205, 198, 186), rect.move(0, 1), border_radius=5)
                pygame.draw.rect(s, (255, 253, 247), rect, border_radius=5)
                pygame.draw.rect(s, (218, 210, 196), rect, 1, border_radius=5)
    # safe stars (non-start safe cells) + start arrows
    for idx in SAFE_RING:
        c, r_ = RING[idx]
        cx, cy = _cell(c, r_).center
        if idx in START_OFFSET:
            pi = START_OFFSET.index(idx)
            col = PLAYER_COLORS[pi] if pi in active else (150, 150, 162)
            pygame.draw.polygon(s, (255, 255, 255), star_points(cx, cy, 9, 4))
            pygame.draw.polygon(s, shade(col, .6), star_points(cx, cy, 9, 4), 1)
        else:
            pygame.draw.polygon(s, (236, 190, 70), star_points(cx, cy, 9.5, 4.2))
            pygame.draw.polygon(s, (170, 120, 30), star_points(cx, cy, 9.5, 4.2), 1)

    # --- centre ------------------------------------------------------------
    c0 = MARGIN + 6 * CELL
    tl, tr = (c0, c0), (c0 + 3 * CELL, c0)
    bl, br = (c0, c0 + 3 * CELL), (c0 + 3 * CELL, c0 + 3 * CELL)
    ctr = (c0 + 1.5 * CELL, c0 + 1.5 * CELL)
    tris = (( tl, bl), (tl, tr), (tr, br), (bl, br))          # red(left) green(top) blue(right) yellow(bottom)
    for pi, (a, b) in enumerate(tris):
        col = PLAYER_COLORS[pi] if pi in active else (150, 150, 162)
        pygame.draw.polygon(s, col, [a, b, ctr])
        pygame.draw.polygon(s, shade(col, .6), [a, b, ctr], 2)
    pygame.draw.circle(s, (30, 22, 60), ctr, 21)
    pygame.draw.circle(s, GOLD, ctr, 21, 2)
    s.blit(crown_surface(26), crown_surface(26).get_rect(center=(ctr[0], ctr[1] - 3)))
    draw_text(s, "LUDO", 8, GOLD_LIGHT, (ctr[0], ctr[1] + 10))
    pygame.draw.rect(s, GOLD_DARK, pygame.Rect(c0, c0, 3 * CELL, 3 * CELL), 2)
    pygame.draw.rect(s, (60, 40, 100), plate, 2, border_radius=14)
    return s


def board_surface(active) -> pygame.Surface:
    """Cached board for a set of PARTICIPATING colour ids (an int n means colours 0..n-1)."""
    key = frozenset(range(active)) if isinstance(active, int) else frozenset(active)
    if key not in _cache:
        _cache[key] = _render(key)
    return _cache[key]


@lru_cache(maxsize=64)
def token_sprite(color, r: int) -> pygame.Surface:
    pad = 5
    size = 2 * r + 2 * pad
    s = pygame.Surface((size, size + 3), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    pygame.draw.ellipse(s, (0, 0, 0, 95), (cx - r * .95, cy + r * .45, r * 1.9, r * .9))
    pygame.draw.circle(s, shade(color, .5), (cx, cy), r)
    for i in range(r - 1, 0, -1):
        t = i / r
        col = lerp_color(lerp_color(color, (255, 255, 255), .5), shade(color, .95), t ** .8)
        pygame.draw.circle(s, col, (cx - (1 - t) * r * .22, cy - (1 - t) * r * .26 - 1), i)
    pygame.draw.circle(s, shade(color, .72), (cx, cy - 1), int(r * .55), 1)
    hl = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.ellipse(hl, (255, 255, 255, 150), (cx - r * .55, cy - r * .85, r * .8, r * .45))
    s.blit(hl, (0, 0))
    return s
