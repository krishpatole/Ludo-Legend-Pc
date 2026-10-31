"""Main menu + options screen with an animated backdrop."""
from __future__ import annotations
import math, random
import pygame
from config.settings import *
from audio.audio_manager import get_audio
from ui.buttons import Button
from ui.board_view import token_sprite
from ui.dice_view import die_face
from utils.helpers import (draw_text, draw_glow, crown_surface, gradient_text, get_background, approach, shade,
                           lerp_color)


class Backdrop:
    """Slowly drifting dice + tokens behind menu screens."""

    def __init__(self, n=16):
        rnd = random.Random(3)
        self.items = [dict(x=rnd.uniform(0, WIDTH), y=rnd.uniform(0, HEIGHT), v=rnd.uniform(10, 30),
                           kind=rnd.choice(("die", "tok")), c=rnd.randrange(4), val=rnd.randint(1, 6),
                           ph=rnd.uniform(0, 6), s=rnd.uniform(.6, 1.4)) for _ in range(n)]

    def update(self, dt):
        for it in self.items:
            it["y"] -= it["v"] * dt
            it["ph"] += dt
            if it["y"] < -60:
                it["y"], it["x"] = HEIGHT + 60, random.uniform(0, WIDTH)

    def draw(self, surf):
        surf.blit(get_background(), (0, 0))
        for it in self.items:
            x, y = it["x"] + math.sin(it["ph"]) * 14, it["y"]
            if it["kind"] == "die":
                img = pygame.transform.rotozoom(die_face(it["val"], 56), math.sin(it["ph"] * .6) * 25, it["s"] * .9)
            else:
                img = pygame.transform.rotozoom(token_sprite(PLAYER_COLORS[it["c"]], 14), 0, it["s"] * 1.8)
            img = img.copy()
            img.set_alpha(46)
            surf.blit(img, img.get_rect(center=(x, y)))


def draw_title(surf, t, cy=150, crown_w=112):
    cx = WIDTH // 2
    bob = math.sin(t * 2) * 5
    draw_glow(surf, (cx, cy - 40), 170, GOLD, .28 + .08 * math.sin(t * 2))
    c = crown_surface(crown_w)
    surf.blit(c, c.get_rect(center=(cx, cy - 46 + bob)))
    sh = gradient_text("LUDO LEGENDS", 82, (40, 20, 70), (40, 20, 70))
    surf.blit(sh, sh.get_rect(center=(cx + 4, cy + 54 + 5)))
    title = gradient_text("LUDO LEGENDS", 82, (255, 240, 170), (226, 150, 38))
    surf.blit(title, title.get_rect(center=(cx, cy + 54)))
    draw_text(surf, TAGLINE, 24, (200, 205, 240), (cx, cy + 118), shadow=(0, 0, 0))


class MenuScreen:
    def __init__(self, on_action):
        self.t = 0.0
        self.back = Backdrop()
        cx = WIDTH // 2
        self.buttons = [Button((cx - 170, 360 + i * 84, 340, 66), lab, st, 30, lambda a=act: on_action(a))
                        for i, (lab, st, act) in enumerate((("PLAY", "gold", "play"), ("OPTIONS", "violet", "options"),
                                                            ("EXIT", "slate", "exit")))]
        self.audio = get_audio()

    def handle_event(self, e):
        for b in self.buttons:
            if b.handle(e):
                self.audio.play("click")
                return

    def update(self, dt):
        self.t += dt
        self.back.update(dt)
        m = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update(dt, m)

    def draw(self, surf):
        self.back.draw(surf)
        draw_title(surf, self.t)
        for b in self.buttons:
            b.draw(surf)
        draw_text(surf, "Local multiplayer  •  2-4 players", 15, (130, 138, 180), (WIDTH // 2, HEIGHT - 26))


class Toggle:
    def __init__(self, rect, label, attr):
        self.rect, self.label, self.attr = pygame.Rect(rect), label, attr
        self.k = 1.0 if getattr(SETTINGS, attr) else 0.0
        self.hover = 0.0

    def value(self):
        return getattr(SETTINGS, self.attr)

    def handle(self, e) -> bool:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            setattr(SETTINGS, self.attr, not self.value())
            return True
        return False

    def update(self, dt, m):
        self.k = approach(self.k, 1.0 if self.value() else 0.0, 16, dt)
        self.hover = approach(self.hover, 1.0 if self.rect.collidepoint(m) else 0.0, 14, dt)

    def draw(self, surf):
        r = self.rect
        pygame.draw.rect(surf, lerp_color((26, 30, 64), (40, 46, 96), self.hover), r, border_radius=18)
        pygame.draw.rect(surf, lerp_color((70, 76, 120), GOLD, self.hover), r, 2, border_radius=18)
        draw_text(surf, self.label, 26, WHITE, (r.x + 30, r.centery), "midleft", shadow=(0, 0, 0))
        tw, th = 150, 44
        tr = pygame.Rect(r.right - tw - 26, r.centery - th // 2, tw, th)
        on = lerp_color((90, 54, 64), (52, 170, 100), self.k)
        pygame.draw.rect(surf, on, tr, border_radius=th // 2)
        pygame.draw.rect(surf, shade(on, .6), tr, 2, border_radius=th // 2)
        kx = tr.x + th // 2 + (tw - th) * self.k
        pygame.draw.circle(surf, (0, 0, 0), (kx, tr.centery + 2), th // 2 - 3)
        pygame.draw.circle(surf, WHITE, (kx, tr.centery), th // 2 - 3)
        draw_text(surf, "ON" if self.value() else "OFF", 18, WHITE,
                  (tr.x + (th + tw) // 2 - 14 if not self.value() else tr.x + 38, tr.centery))


class OptionsScreen:
    def __init__(self, on_back, on_changed):
        self.t = 0.0
        self.back = Backdrop(10)
        cx = WIDTH // 2
        self.toggles = [Toggle((cx - 300, 205 + i * 76, 600, 62), lab, attr)
                        for i, (lab, attr) in enumerate((("MUSIC", "music"), ("SFX", "sfx"), ("ANIMATIONS", "animations"),
                                                         ("BOMBS", "bombs")))]
        self.btn = Button((cx - 130, 545, 260, 62), "BACK", "gold", 28, on_back)
        self.on_changed = on_changed
        self.audio = get_audio()

    def handle_event(self, e):
        for tg in self.toggles:
            if tg.handle(e):
                self.audio.play("click")
                self.on_changed()
        if self.btn.handle(e):
            self.audio.play("click")

    def update(self, dt):
        self.t += dt
        self.back.update(dt)
        m = pygame.mouse.get_pos()
        for tg in self.toggles:
            tg.update(dt, m)
        self.btn.update(dt, m)

    def draw(self, surf):
        self.back.draw(surf)
        c = crown_surface(60)
        surf.blit(c, c.get_rect(center=(WIDTH // 2, 80)))
        draw_text(surf, "OPTIONS", 52, GOLD_LIGHT, (WIDTH // 2, 150), shadow=(0, 0, 0))
        for tg in self.toggles:
            tg.draw(surf)
        self.btn.draw(surf)
