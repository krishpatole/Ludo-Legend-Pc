"""Victory overlay: rays, crown, confetti (spawned by the scene), PLAY AGAIN / MAIN MENU."""
from __future__ import annotations
import math
import pygame
from config.settings import WIDTH, HEIGHT, GOLD, GOLD_LIGHT, GOLD_DARK, WHITE
from ui.buttons import Button
from utils.helpers import (draw_text, draw_text_fit, draw_glow, crown_surface, gradient_text, clamp, ease_out_back,
                           ease_out_cubic, shade)


class VictoryOverlay:
    DELAY = 0.9

    def __init__(self, winner: int, color, on_exit, name: str | None = None):
        self.winner, self.color, self.on_exit = winner, color, on_exit
        self.name = (name or f"PLAYER {winner + 1}").upper()
        self.t = 0.0
        cx = WIDTH // 2
        self.btn_again = Button((cx - 230, 520, 220, 62), "PLAY AGAIN", "gold", 24, lambda: on_exit("again"))
        self.btn_menu = Button((cx + 10, 520, 220, 62), "MAIN MENU", "slate", 24, lambda: on_exit("menu"))

    def update(self, dt):
        self.t += dt
        m = pygame.mouse.get_pos()
        self.btn_again.update(dt, m)
        self.btn_menu.update(dt, m)

    def handle(self, e):
        if self.t < self.DELAY + .4:
            return
        self.btn_again.handle(e)
        self.btn_menu.handle(e)

    def draw(self, surf, t):
        k = clamp((self.t - .15) / .5)
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((6, 6, 20, int(190 * k)))
        surf.blit(veil, (0, 0))
        cx, cy = WIDTH // 2, 300
        # rotating rays in the winner's colour
        rays = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(14):
            a0 = self.t * .35 + i * (2 * math.pi / 14)
            a1 = a0 + .13
            pts = [(cx, cy), (cx + math.cos(a0) * 900, cy + math.sin(a0) * 900), (cx + math.cos(a1) * 900, cy + math.sin(a1) * 900)]
            pygame.draw.polygon(rays, (*self.color, 34), pts)
        surf.blit(rays, (0, 0))
        draw_glow(surf, (cx, cy), 330, self.color, .35 * k)
        s = ease_out_back(clamp((self.t - .1) / .6))
        crown = crown_surface(110)
        c2 = pygame.transform.smoothscale(crown, (max(2, int(110 * s)), max(2, int(crown.get_height() * s))))
        surf.blit(c2, c2.get_rect(center=(cx, 170 + 5 * math.sin(self.t * 3))))
        title = gradient_text("LUDO LEGENDS", 46, (255, 236, 160), (222, 150, 40))
        surf.blit(title, title.get_rect(center=(cx, 252)))
        txt = f"{self.name} WINS!"
        draw_text_fit(surf, txt, int(76 * s) + 1, self.color, (cx, 345), WIDTH - 140, shadow=(0, 0, 0), min_size=24)
        draw_text(surf, "ALL FOUR TOKENS HOME", 20, GOLD_LIGHT, (cx, 410), alpha=255 * k)
        if self.t > self.DELAY:
            a = clamp((self.t - self.DELAY) / .4)
            self.btn_again.draw(surf)
            self.btn_menu.draw(surf)
