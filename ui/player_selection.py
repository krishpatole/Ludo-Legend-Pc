"""SELECT PLAYERS screen: three large cards with colour token previews."""
from __future__ import annotations
import math
import pygame
from config.settings import *
from audio.audio_manager import get_audio
from ui.buttons import Button
from ui.board_view import token_sprite
from ui.menu import Backdrop
from game.setup import DEFAULT_COLOURS, COLOUR_NAMES
from utils.helpers import draw_text, draw_glow, approach, shade, lerp_color, crown_surface


class PlayerSelectScreen:
    def __init__(self, on_choose, on_back):
        self.t = 0.0
        self.back = Backdrop(12)
        self.on_choose = on_choose
        cw, ch, gap = 270, 340, 40
        x0 = WIDTH // 2 - (3 * cw + 2 * gap) // 2
        self.cards = [dict(n=n, rect=pygame.Rect(x0 + i * (cw + gap), 200, cw, ch), hover=0.0, press=0.0)
                      for i, n in enumerate((2, 3, 4))]
        self.btn_back = Button((WIDTH // 2 - 110, 610, 220, 56), "BACK", "slate", 26, on_back)
        self.audio = get_audio()

    def handle_event(self, e):
        for c in self.cards:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and c["rect"].collidepoint(e.pos):
                c["press"] = 1.0
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and c["press"] and c["rect"].collidepoint(e.pos):
                self.audio.play("click")
                self.on_choose(c["n"])
                return
        if self.btn_back.handle(e):
            self.audio.play("click")

    def update(self, dt):
        self.t += dt
        self.back.update(dt)
        m = pygame.mouse.get_pos()
        for c in self.cards:
            c["hover"] = approach(c["hover"], 1.0 if c["rect"].collidepoint(m) else 0.0, 14, dt)
            c["press"] = approach(c["press"], 0.0, 12, dt) if not pygame.mouse.get_pressed()[0] else c["press"]
        self.btn_back.update(dt, m)

    def draw(self, surf):
        self.back.draw(surf)
        cr = crown_surface(54)
        surf.blit(cr, cr.get_rect(center=(WIDTH // 2, 70)))
        draw_text(surf, "SELECT PLAYERS", 56, GOLD_LIGHT, (WIDTH // 2, 134), shadow=(0, 0, 0))
        draw_text(surf, "Choose how many will play — names and colours come next", 20, (170, 178, 215), (WIDTH // 2, 176))
        for c in self.cards:
            h, n = c["hover"], c["n"]
            r = c["rect"].copy()
            r.y -= int(10 * h) - int(5 * (1 if c["press"] > .5 else 0))
            if h > .05:
                draw_glow(surf, r.center, 230, GOLD, .25 * h)
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (18, 20, 50, 230), panel.get_rect(), border_radius=24)
            surf.blit(panel, r.topleft)
            pygame.draw.rect(surf, lerp_color((90, 96, 150), GOLD, h), r, 3, border_radius=24)
            draw_text(surf, f"{n} PLAYERS", 34, WHITE, (r.centerx, r.y + 50), shadow=(0, 0, 0))
            # colour swatches + token previews (2x2 grid per colour pair)
            for i in range(4):
                active = i in DEFAULT_COLOURS[n]          # preview of the seats in use (colours are chosen later)
                col = PLAYER_COLORS[i]
                bx = r.x + 52 + (i % 2) * 166
                by = r.y + 130 + (i // 2) * 100
                pr = pygame.Rect(0, 0, 110, 80)
                pr.center = (bx + 25, by + 20)
                pygame.draw.rect(surf, shade(col, .45 if active else .25), pr, border_radius=14)
                pygame.draw.rect(surf, col if active else (70, 72, 90), pr, 2, border_radius=14)
                spr = token_sprite(col if active else (92, 94, 110), 13)
                for k in range(4):
                    surf.blit(spr, spr.get_rect(center=(pr.x + 28 + (k % 2) * 26 + 3, pr.y + 26 + (k // 2) * 26 + 3)))
                draw_text(surf, COLOUR_NAMES[i], 12, WHITE if active else (110, 112, 135), (pr.centerx, pr.y + 12))
            draw_text(surf, "PLAY", 20, GOLD_LIGHT if h > .5 else (150, 158, 195), (r.centerx, r.bottom - 26))
        self.btn_back.draw(surf)
