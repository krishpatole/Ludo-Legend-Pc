"""Premium collectible-style power cards: face renderer, hand view and centre-flight animation."""
from __future__ import annotations
import math
from functools import lru_cache
import pygame
from config.settings import (CARD_W, CARD_H, GOLD, GOLD_LIGHT, GOLD_DARK, WIDTH, HEIGHT,
                             BOARD_X, BOARD_Y, BOARD_SIZE, PLAYER_COLORS)
from powers.power_card import PowerType, CARD_INFO
from utils.helpers import (font, draw_text_fit, draw_glow, shade, lerp_color, gradient_surface, clamp, approach,
                           ease_out_cubic, ease_in_out, draw_pips, draw_text, lerp)

SS = 2          # supersampling factor for crisp small text


def _fit(text, max_w, size, bold=True):
    while size > 6 and font(size, bold).size(text)[0] > max_w:
        size -= 1
    return font(size, bold).render(text, True, (255, 255, 255)), size


def _icon_shield(s, cx, cy, r, acc):
    pts = [(cx - .85 * r, cy - .8 * r), (cx, cy - r), (cx + .85 * r, cy - .8 * r), (cx + .85 * r, cy + .1 * r),
           (cx, cy + r), (cx - .85 * r, cy + .1 * r)]
    pygame.draw.polygon(s, shade(acc, .55), [(x, y + r * .08) for x, y in pts])
    pygame.draw.polygon(s, acc, pts)
    inner = [(cx + (x - cx) * .74, cy + (y - cy) * .74 + r * .02) for x, y in pts]
    pygame.draw.polygon(s, lerp_color(acc, (20, 40, 110), .55), inner)
    w = max(2, int(r * .2))
    pygame.draw.lines(s, (255, 255, 255), False, [(cx - .32 * r, cy + .02 * r), (cx - .06 * r, cy + .3 * r), (cx + .38 * r, cy - .3 * r)], w)


def _icon_dice(s, cx, cy, r, acc):
    for dx, dy, v, rot in ((-.35, -.3, 3, 0), (.3, .25, 5, 0)):
        side = r * 1.25
        rect = pygame.Rect(0, 0, side, side)
        rect.center = (cx + dx * r, cy + dy * r)
        pygame.draw.rect(s, shade(acc, .5), rect.move(0, r * .08), border_radius=int(side * .2))
        pygame.draw.rect(s, (252, 250, 255), rect, border_radius=int(side * .2))
        pygame.draw.rect(s, acc, rect, max(1, int(r * .06)), border_radius=int(side * .2))
        draw_pips(s, rect, v, (60, 30, 100))


def _icon_skip(s, cx, cy, r, acc):
    for dx in (-.42, .12):
        tri = [(cx + (dx - .02) * r, cy - .62 * r), (cx + (dx + .55) * r, cy), (cx + (dx - .02) * r, cy + .62 * r)]
        pygame.draw.polygon(s, shade(acc, .55), [(x, y + r * .07) for x, y in tri])
        pygame.draw.polygon(s, acc, tri)
    bar = pygame.Rect(0, 0, r * .2, r * 1.24)
    bar.center = (cx + .78 * r, cy)
    pygame.draw.rect(s, shade(acc, .55), bar.move(0, r * .07), border_radius=3)
    pygame.draw.rect(s, acc, bar, border_radius=3)


ICONS = {PowerType.SHIELD: _icon_shield, PowerType.DOUBLE_DICE: _icon_dice, PowerType.SKIP: _icon_skip}


def draw_card_icon(surf, kind, cx, cy, r, accent=None):
    ICONS[kind](surf, cx, cy, r, accent or CARD_INFO[kind].accent)


@lru_cache(maxsize=24)
def card_face(kind: PowerType, w: int, h: int) -> pygame.Surface:
    """Render the full collectible card once (cached)."""
    info = CARD_INFO[kind]
    W, H = w * SS, h * SS
    k = W / 72.0
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    rad = int(11 * k)
    # outer gold frame
    s.blit(gradient_surface(W, H, GOLD_LIGHT, GOLD_DARK, rad), (0, 0))
    pygame.draw.rect(s, shade(GOLD_DARK, .7), (0, 0, W, H), max(1, int(k)), border_radius=rad)
    # body
    b = int(3.5 * k)
    s.blit(gradient_surface(W - 2 * b, H - 2 * b, info.top, info.bottom, rad - b // 2), (b, b))
    # decorative inner border + corner studs
    ib = int(6.5 * k)
    pygame.draw.rect(s, (*info.accent, 200), (ib, ib, W - 2 * ib, H - 2 * ib), max(1, int(.9 * k)), border_radius=int(7 * k))
    for sx, sy in ((ib, ib), (W - ib, ib), (ib, H - ib), (W - ib, H - ib)):
        pygame.draw.circle(s, GOLD_LIGHT, (sx, sy), max(2, int(1.5 * k)))
    # radial spotlight behind the icon (own layer: draw.circle REPLACES pixels on alpha surfaces)
    cx, cy, ir = W // 2, int(33 * k), int(16 * k)
    spot = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        pygame.draw.circle(spot, (*info.accent, 14 * (7 - i)), (cx, cy), int(ir * (1 + i * .22)))
    pygame.draw.circle(spot, (10, 12, 40, 190), (cx, cy), int(ir * 1.12))
    s.blit(spot, (0, 0))
    pygame.draw.circle(s, GOLD_LIGHT, (cx, cy), int(ir * 1.12), max(1, int(k)))
    ICONS[kind](s, cx, cy, ir * .82, info.accent)
    # top label
    lab = font(int(6.2 * k), True).render("POWER CARD", True, GOLD_LIGHT)
    s.blit(lab, lab.get_rect(center=(W // 2, int(12.5 * k))))
    # name
    name, _ = _fit(info.name, W - 2 * ib - int(4 * k), int(11 * k))
    pygame.draw.line(s, (*GOLD, 160), (ib + int(4 * k), int(52 * k)), (W - ib - int(4 * k), int(52 * k)), max(1, int(.7 * k)))
    s.blit(name, name.get_rect(center=(W // 2, int(59 * k))))
    for i, line in enumerate(info.desc):
        t = font(int(7.3 * k), False).render(line, True, (230, 236, 255))
        s.blit(t, t.get_rect(center=(W // 2, int((70 + i * 8.6) * k))))
    # gloss: soft diagonal highlight on the upper-left, clipped to the card silhouette
    gl = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(gl, (255, 255, 255, 34), [(0, 0), (W * .72, 0), (0, H * .5)])
    clip = s.copy()
    clip.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
    gl.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(gl, (0, 0))
    out = pygame.transform.smoothscale(s, (w, h))
    return out


@lru_cache(maxsize=24)
def _shine_band(h: int) -> pygame.Surface:
    w = 22
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for x in range(w):
        v = int(95 * math.sin(math.pi * x / w) ** 2)
        pygame.draw.line(s, (v, v, v), (x, 0), (x, h))
    return pygame.transform.rotate(s, 0)


class CardView:
    """A card sitting in a player's hand. Position is animated toward its slot."""

    def __init__(self, owner: int, kind: PowerType, center):
        self.owner, self.kind = owner, kind
        self.x, self.y = center
        self.tx, self.ty = center
        self.hover = 0.0
        self.press = 0.0
        self.deny = 0.0
        self.phase = (kind.value.__hash__() % 100) / 100

    def set_target(self, center):
        self.tx, self.ty = center

    @property
    def rect(self) -> pygame.Rect:
        r = pygame.Rect(0, 0, CARD_W, CARD_H)
        r.center = (self.x, self.y)
        return r

    def update(self, dt, mouse, interactive: bool):
        self.x = approach(self.x, self.tx, 12, dt)
        self.y = approach(self.y, self.ty, 12, dt)
        self.deny = max(0.0, self.deny - dt)
        over = interactive and self.rect.collidepoint(mouse)
        self.hover = approach(self.hover, 1.0 if over else 0.0, 16, dt)

    def draw(self, surf, mode: str, t: float, color):
        """mode: 'active' (clickable) | 'locked' (my turn but dice rolled) | 'dim' (other player)."""
        h = self.hover if mode == "active" else 0.0
        face = card_face(self.kind, CARD_W, CARD_H)
        lift = 6 * h
        cx, cy = self.x + math.sin(self.deny * 55) * 4 * (self.deny / .3), self.y - lift
        sc = 1 + 0.13 * h
        w, hh = int(CARD_W * sc), int(CARD_H * sc)
        # shadow
        sh = pygame.Surface((w + 16, hh + 16), pygame.SRCALPHA)
        for i in range(4):
            pygame.draw.rect(sh, (0, 0, 0, 26), (8 - i * 2, 8 - i * 2 + 4, w + i * 4, hh + i * 4), border_radius=12 + i * 2)
        alpha_mul = 1.0 if mode == "active" else (0.78 if mode == "locked" else 0.42)
        sh.set_alpha(int(255 * alpha_mul))
        surf.blit(sh, (cx - w / 2 - 8, cy - hh / 2 - 8 + 4 + lift * .6))
        if mode == "active":
            pulse = .30 + .12 * math.sin(t * 3 + self.phase * 6) + .35 * h
            draw_glow(surf, (cx, cy), int(max(w, hh) * .78), CARD_INFO[self.kind].accent, pulse)
        img = face
        if mode == "active":
            img = face.copy()
            sweep = (t * .45 + self.phase) % 1.6 - .3
            band = _shine_band(CARD_H)
            img.blit(band, (int(sweep * (CARD_W + 22)) - 22, 0), special_flags=pygame.BLEND_RGB_ADD)
        if sc != 1:
            img = pygame.transform.smoothscale(img, (w, hh))
        if alpha_mul < 1:
            img = img.copy() if img is face else img
            img.set_alpha(int(255 * alpha_mul))
        surf.blit(img, img.get_rect(center=(cx, cy)))
        if mode == "active":
            pygame.draw.rect(surf, lerp_color(GOLD, (255, 255, 255), h), (cx - w / 2, cy - hh / 2, w, hh),
                             2 if h < .5 else 3, border_radius=12)
        elif mode == "dim":
            veil = pygame.Surface((w, hh), pygame.SRCALPHA)
            pygame.draw.rect(veil, (8, 10, 28, 70), veil.get_rect(), border_radius=12)
            surf.blit(veil, (cx - w / 2, cy - hh / 2))


class CardFlight:
    """The 'used card' animation: hand -> board centre (bigger, glowing) -> hold -> fade away."""
    FLY, EXIT = 0.65, 0.5

    def __init__(self, view: CardView, lines, color, total):
        self.kind, self.lines, self.color, self.total = view.kind, lines, color, total
        self.start = (view.x, view.y)
        self.center = (BOARD_X + BOARD_SIZE / 2, BOARD_Y + BOARD_SIZE / 2 - 30)
        self.t = 0.0
        self.big = (int(CARD_W * 2.0), int(CARD_H * 2.0))

    @property
    def done(self):
        return self.t >= self.total

    @property
    def landed(self):
        return self.t >= self.FLY

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        t, info = self.t, CARD_INFO[self.kind]
        fly = ease_out_cubic(t / self.FLY)
        ex = clamp((t - (self.total - self.EXIT)) / self.EXIT)
        # darken the board a little while the card is shown
        veil = pygame.Surface((BOARD_SIZE + 20, BOARD_SIZE + 20), pygame.SRCALPHA)
        pygame.draw.rect(veil, (6, 8, 24, int(170 * fly * (1 - ex))), veil.get_rect(), border_radius=24)
        surf.blit(veil, (BOARD_X - 10, BOARD_Y - 10))
        x, y = lerp(self.start[0], self.center[0], fly), lerp(self.start[1], self.center[1], fly)
        y -= 40 * ease_in_out(ex)
        sc = lerp(1.0, 2.0, fly) * (1 + .25 * ex) + (.03 * math.sin(t * 6) if self.landed else 0)
        w, h = int(CARD_W * sc), int(CARD_H * sc)
        alpha = int(255 * (1 - ex))
        draw_glow(surf, (x, y), int(max(w, h) * .85), info.accent, (.45 + .2 * math.sin(t * 7)) * (1 - ex) * min(1, fly * 1.4))
        face = card_face(self.kind, self.big[0], self.big[1])
        img = pygame.transform.smoothscale(face, (w, h))
        img.set_alpha(alpha)
        surf.blit(img, img.get_rect(center=(x, y)))
        pygame.draw.rect(surf, (*GOLD_LIGHT,), img.get_rect(center=(x, y)), 3, border_radius=int(14 * sc / 2))
        if self.landed:
            ta = clamp((t - self.FLY) / .25) * (1 - ex)
            base_y = y + h / 2 + 26
            draw_text(surf, self.lines[0], 34, info.accent, (self.center[0], base_y), shadow=(0, 0, 0), alpha=255 * ta)
            draw_text_fit(surf, self.lines[1], 20, lerp_color(self.color, (255, 255, 255), .5), (self.center[0], base_y + 30), 430, shadow=(0, 0, 0), alpha=255 * ta, min_size=10)
            draw_text_fit(surf, self.lines[2], 17, (240, 244, 255), (self.center[0], base_y + 54), 430, shadow=(0, 0, 0), alpha=255 * ta, min_size=10)
