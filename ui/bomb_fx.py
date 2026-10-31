"""Bomb visuals: the bomb icon, flashing danger squares and the expanding blast rings."""
from __future__ import annotations
import math
import pygame
from config.settings import CELL
from game.board import RING, to_px
from utils.helpers import clamp, draw_glow

DANGER = (255, 70, 60)


def ring_cell_rect(ring_idx: int) -> pygame.Rect:
    c, r = RING[ring_idx]
    x, y = to_px(c, r)
    return pygame.Rect(int(x), int(y), CELL, CELL)


def draw_bomb_icon(surf, cx, cy, r, t=0.0):
    """A little round black bomb with a highlight and a sparking fuse."""
    pygame.draw.circle(surf, (0, 0, 0), (cx + 1, cy + 2), r)                       # shadow
    pygame.draw.circle(surf, (38, 38, 52), (cx, cy), r)
    pygame.draw.circle(surf, (86, 88, 112), (cx - r * .3, cy - r * .3), max(2, int(r * .35)))
    pygame.draw.rect(surf, (120, 120, 140), (cx - r * .3, cy - r - r * .22, r * .6, r * .32), border_radius=2)   # cap
    fx, fy = cx + r * .55, cy - r * 1.35                                            # fuse end
    pygame.draw.lines(surf, (200, 160, 90), False, [(cx + r * .1, cy - r - r * .1), (cx + r * .45, cy - r * 1.2), (fx, fy)], max(1, int(r * .16)))
    spark = .5 + .5 * math.sin(t * 22)
    pygame.draw.circle(surf, (255, int(180 + 60 * spark), 60), (fx, fy), max(2, int(r * (.3 + .2 * spark))))


def draw_danger_cells(surf, cells, t: float, k: float, sx=0, sy=0):
    """Flash the marked squares red; the flashing speeds up as the explosion gets closer (k: 0..1)."""
    pulse = .5 + .5 * math.sin(t * (6 + 12 * k))
    for idx in cells:
        r = ring_cell_rect(idx).move(int(sx), int(sy))
        c = r.center
        draw_glow(surf, c, CELL, DANGER, .25 + .45 * pulse)
        box = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(box, (*DANGER, int(95 + 130 * pulse)), box.get_rect(), border_radius=6)
        surf.blit(box, r.topleft)
        pygame.draw.rect(surf, (255, 235, 220), r, 3 if pulse > .5 else 2, border_radius=6)


def draw_danger_icons(surf, cells, t: float, sx=0, sy=0):
    """The bomb icon sits in the corner of each marked square, drawn ABOVE the tokens so it is never hidden."""
    for idx in cells:
        r = ring_cell_rect(idx).move(int(sx), int(sy))
        pygame.draw.circle(surf, (255, 235, 220), (r.right - 8, r.y + 8), 10)
        pygame.draw.circle(surf, DANGER, (r.right - 8, r.y + 8), 10, 2)
        draw_bomb_icon(surf, r.right - 8, r.y + 10, 6, t)


class BlastFX:
    """Expanding shock rings + a white flash for each exploded square."""

    def __init__(self):
        self.items: list[list] = []          # [x, y, age]

    def add(self, pos):
        self.items.append([pos[0], pos[1], 0.0])

    def update(self, dt):
        for it in self.items:
            it[2] += dt
        self.items = [it for it in self.items if it[2] < .7]

    def draw(self, surf):
        for x, y, age in self.items:
            k = clamp(age / .7)
            if k < .35:
                draw_glow(surf, (x, y), 46, (255, 255, 255), 1 - k / .35)
            draw_glow(surf, (x, y), int(30 + 30 * k), (255, 150, 40), (1 - k) * .8)
            rad = int(8 + 52 * k)
            ring = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (255, 200, 90, int(230 * (1 - k))), (rad + 4, rad + 4), rad, max(2, int(5 * (1 - k))))
            surf.blit(ring, ring.get_rect(center=(x, y)))
