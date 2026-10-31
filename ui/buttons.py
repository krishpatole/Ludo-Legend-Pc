"""Premium rounded buttons with hover / press animation and soft shadow."""
from __future__ import annotations
import pygame
from config.settings import GOLD, GOLD_LIGHT, GOLD_DARK, INK
from utils.helpers import approach, draw_text, shade, lerp_color

STYLES = {
    "gold": ((255, 214, 110), (214, 150, 40), (60, 36, 6)),
    "violet": ((140, 110, 235), (84, 56, 176), (255, 255, 255)),
    "slate": ((88, 98, 140), (48, 54, 92), (240, 244, 255)),
    "danger": ((232, 98, 98), (166, 44, 56), (255, 255, 255)),
}


class Button:
    def __init__(self, rect, label, style="gold", size=26, on_click=None):
        self.rect = pygame.Rect(rect)
        self.label, self.style, self.size, self.on_click = label, style, size, on_click
        self.hover = 0.0
        self.press = 0.0
        self._down = False
        self.enabled = True

    def update(self, dt, mouse):
        over = self.enabled and self.rect.collidepoint(mouse)
        self.hover = approach(self.hover, 1.0 if over else 0.0, 14, dt)
        self.press = approach(self.press, 1.0 if self._down else 0.0, 30, dt)

    def handle(self, event) -> bool:
        """Returns True on a completed click (mouse released over the button)."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self._down = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was, self._down = self._down, False
            if was and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surf, alpha=255):
        top, bot, txt = STYLES.get(self.style, STYLES["gold"])
        h, p = self.hover, self.press
        scale = 1 + 0.045 * h - 0.06 * p
        r = self.rect.copy()
        r.size = (int(self.rect.w * scale), int(self.rect.h * scale))
        r.center = self.rect.center
        rad = r.h // 2 if r.h < 70 else 18
        lift = int(3 * h) - int(4 * p)
        body = r.move(0, -lift)
        sh = pygame.Surface((r.w + 24, r.h + 24), pygame.SRCALPHA)
        for i in range(6):
            pygame.draw.rect(sh, (0, 0, 0, 20), (12 - i * 2, 14 - i * 2 + lift, r.w + i * 4, r.h + i * 4), border_radius=rad + i * 2)
        surf.blit(sh, (r.x - 12, r.y - 12 + 4))
        b = shade(bot, .72)
        pygame.draw.rect(surf, b, body.move(0, 4), border_radius=rad)           # bottom lip (depth)
        pygame.draw.rect(surf, lerp_color(bot, top, .25 + .25 * h), body, border_radius=rad)
        gloss = pygame.Rect(body.x + 3, body.y + 3, body.w - 6, body.h // 2)
        pygame.draw.rect(surf, lerp_color(top, (255, 255, 255), .1 + .12 * h), gloss,
                         border_top_left_radius=rad, border_top_right_radius=rad,
                         border_bottom_left_radius=rad // 3, border_bottom_right_radius=rad // 3)
        pygame.draw.rect(surf, shade(top, 1.15) if self.enabled else (110, 110, 120), body, 2, border_radius=rad)
        col = txt if self.enabled else (170, 170, 180)
        draw_text(surf, self.label, int(self.size * (1 + .03 * h)), col, body.center)
