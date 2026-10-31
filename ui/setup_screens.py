"""Setup flow after the player-count screen:  NAMES -> COLOURS -> REVIEW  (then the game starts).

All state lives in a game.setup.SetupDraft, so going back and forward never loses anything.
"""
from __future__ import annotations
import math
import pygame
from config.settings import *
from audio.audio_manager import get_audio
from game.setup import MAX_NAME_LEN, COLOUR_NAMES, SEAT_NAMES, OPPOSITE, clean_name, default_name
from ui.board_view import token_sprite
from ui.buttons import Button
from ui.menu import Backdrop
from utils.helpers import (draw_text, draw_text_fit, draw_glow, crown_surface, approach, shade, lerp_color)

CX = WIDTH // 2
BTN_Y = 1130 if PORTRAIT else 656
STEPS = ("PLAYERS", "NAMES", "COLOURS", "REVIEW")
GREY = (92, 94, 112)


def draw_lock(surf, cx, cy, s, col):
    """Tiny padlock icon."""
    body = pygame.Rect(0, 0, int(s * 1.5), int(s * 1.1))
    body.center = (cx, cy + s * .25)
    pygame.draw.arc(surf, col, pygame.Rect(cx - s * .5, cy - s * .85, s, s * 1.2), 0, math.pi, 2)
    pygame.draw.rect(surf, col, body, border_radius=3)


class _Step:
    """Shared look: backdrop, title, step tracker and bottom buttons."""

    def __init__(self, step: int, title: str, subtitle: str):
        self.t = 0.0
        self.step, self.title, self.subtitle = step, title, subtitle
        self.back_drop = Backdrop(8)
        self.audio = get_audio()
        self.buttons: list[Button] = []

    def close(self) -> None:
        pass

    def update(self, dt):
        self.t += dt
        self.back_drop.update(dt)
        m = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update(dt, m)

    def draw_frame(self, surf):
        self.back_drop.draw(surf)
        cr = crown_surface(44)
        surf.blit(cr, cr.get_rect(center=(CX, 44)))
        draw_text(surf, self.title, 44, GOLD_LIGHT, (CX, 98), shadow=(0, 0, 0))
        draw_text_fit(surf, self.subtitle, 18, (170, 178, 215), (CX, 134), WIDTH - 30)
        gap = 150 if PORTRAIT else 170
        x0 = CX - gap * (len(STEPS) - 1) / 2
        for i, lab in enumerate(STEPS):
            x, y = x0 + i * gap, 168
            done, cur = i < self.step, i == self.step
            if i:
                pygame.draw.line(surf, GOLD if (done or cur) else (70, 76, 120), (x - gap + 14, y), (x - 14, y), 3)
            col = GOLD if cur else (110, 200, 140) if done else (80, 86, 130)
            pygame.draw.circle(surf, col, (x, y), 11)
            pygame.draw.circle(surf, shade(col, .5), (x, y), 11, 2)
            draw_text(surf, str(i + 1), 13, INK if (cur or done) else (170, 176, 205), (x, y))
            draw_text(surf, lab, 12, WHITE if cur else (140, 146, 180), (x, y + 24))

    def click_sound(self):
        self.audio.play("click")


# =========================================================================== names
class NamesScreen(_Step):
    FIELD_W, FIELD_H, ROW_H, Y0 = (600, 64, 132, 250) if PORTRAIT else (500, 56, 82, 224)

    def __init__(self, draft, on_back, on_next):
        super().__init__(1, "PLAYER NAMES", "Type a name for each player — leave a box empty to use the default")
        self.draft, self.on_back, self.on_next = draft, on_back, on_next
        self.focus = 0
        self.btn_back = Button((CX - 280, BTN_Y, 240, 58), "BACK", "slate", 26, lambda: (self.click_sound(), on_back()))
        self.btn_next = Button((CX + 40, BTN_Y, 240, 58), "CONTINUE", "gold", 26, self.try_next)
        self.buttons = [self.btn_back, self.btn_next]
        try:                                        # desktop: no-op; phones: shows the on-screen keyboard
            pygame.key.start_text_input()
            pygame.key.set_repeat(400, 35)
        except Exception:
            pass

    def close(self):
        try:
            pygame.key.stop_text_input()
            pygame.key.set_repeat(0)
        except Exception:
            pass

    def field_rect(self, i):
        if PORTRAIT:                                 # label sits above the box
            return pygame.Rect(CX - self.FIELD_W // 2, self.Y0 + 30 + i * self.ROW_H, self.FIELD_W, self.FIELD_H)
        return pygame.Rect(CX - 190, self.Y0 + i * self.ROW_H, self.FIELD_W, self.FIELD_H)

    def try_next(self):
        if self.draft.name_errors():
            self.audio.play("shield_block", .4)
            return
        self.click_sound()
        self.on_next()

    # ---- input ----
    def handle_event(self, e):
        for b in self.buttons:
            b.handle(e)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i in range(self.draft.n):
                if self.field_rect(i).collidepoint(e.pos):
                    self.focus = i
        elif e.type == pygame.TEXTINPUT:
            text = "".join(ch for ch in e.text if ch.isprintable())
            cur = self.draft.names[self.focus]
            if text and len(cur) < MAX_NAME_LEN:
                self.draft.set_name(self.focus, cur + text)          # set_name caps at MAX_NAME_LEN
        elif e.type == pygame.KEYDOWN:
            n = self.draft.n
            if e.key == pygame.K_BACKSPACE:
                self.draft.set_name(self.focus, self.draft.names[self.focus][:-1])
            elif e.key == pygame.K_DELETE:
                self.draft.set_name(self.focus, "")
            elif e.key == pygame.K_TAB:
                step = -1 if (e.mod & pygame.KMOD_SHIFT) else 1
                self.focus = (self.focus + step) % n
            elif e.key == pygame.K_UP:
                self.focus = max(0, self.focus - 1)
            elif e.key == pygame.K_DOWN:
                self.focus = min(n - 1, self.focus + 1)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.focus < n - 1:
                    self.focus += 1
                else:
                    self.try_next()

    # ---- draw ----
    def draw(self, surf):
        self.draw_frame(surf)
        d = self.draft
        errors = d.name_errors()
        self.btn_next.enabled = not errors
        for i in range(d.n):
            r = self.field_rect(i)
            focused = i == self.focus
            if focused:
                draw_glow(surf, r.center, 330, GOLD, .12)
            lab_pos, lab_anchor = ((r.x + 6, r.y - 16), "midleft") if PORTRAIT else ((r.x - 24, r.centery), "midright")
            draw_text(surf, f"PLAYER {i + 1}", 16, GOLD_LIGHT if focused else (150, 158, 195), lab_pos, lab_anchor)
            pygame.draw.rect(surf, (16, 18, 46), r, border_radius=14)
            pygame.draw.rect(surf, GOLD if focused else (84, 90, 140), r, 3 if focused else 2, border_radius=14)
            raw = d.names[i]
            tw = r.w - 110
            if raw:
                tr = draw_text_fit(surf, raw, 26, WHITE, (r.x + 20, r.centery), tw, "midleft", min_size=14)
            else:
                tr = draw_text_fit(surf, default_name(i), 26, (110, 116, 150), (r.x + 20, r.centery), tw, "midleft", min_size=14)
            if focused and int(self.t * 2) % 2 == 0:                   # blinking caret after the typed text
                cx = (tr.right + 3) if raw else (r.x + 20)
                pygame.draw.line(surf, GOLD_LIGHT, (cx, r.centery - 14), (cx, r.centery + 14), 2)
            draw_text(surf, f"{len(raw)}/{MAX_NAME_LEN}", 12, (120, 126, 165), (r.right - 14, r.centery), "midright")
        hy = (self.Y0 + d.n * self.ROW_H + 20) if PORTRAIT else 570
        if errors:
            draw_text_fit(surf, errors[0].upper(), 18, (255, 130, 130), (CX, hy), WIDTH - 40)
        else:
            hint = "Tap a box, then type. Enter moves to the next player." if PORTRAIT else \
                "Tap or click a box, then type. Tab / Enter moves to the next player."
            draw_text_fit(surf, hint, 15, (150, 158, 195), (CX, hy), WIDTH - 40)
        for b in self.buttons:
            b.draw(surf)


# ========================================================================== colours
class ColoursScreen(_Step):
    ROW_H, TILE_W, TILE_H, TILE_GAP = (188, 152, 66, 10) if PORTRAIT else (92, 128, 66, 14)
    PANEL_W = 680 if PORTRAIT else 880

    def __init__(self, draft, on_back, on_next):
        super().__init__(2, "CHOOSE COLOURS", "Every player picks a different colour — taken colours are locked")
        self.draft, self.on_back, self.on_next = draft, on_back, on_next
        self.deny: dict[tuple[int, int], float] = {}
        self.hover = 0.0
        self.hover_tile: tuple[int, int] | None = None
        self.notice = ("", 0.0)
        if PORTRAIT:
            self.btn_back = Button((24, BTN_Y, 190, 58), "BACK", "slate", 24, lambda: (self.click_sound(), on_back()))
            self.btn_auto = Button((226, BTN_Y, 250, 58), "AUTO ASSIGN", "violet", 22, self.do_auto)
            self.btn_next = Button((488, BTN_Y, 208, 58), "CONTINUE", "gold", 24, self.try_next)
        else:
            self.btn_back = Button((CX - 400, BTN_Y, 220, 58), "BACK", "slate", 26, lambda: (self.click_sound(), on_back()))
            self.btn_auto = Button((CX - 130, BTN_Y, 260, 58), "AUTO ASSIGN", "violet", 24, self.do_auto)
            self.btn_next = Button((CX + 180, BTN_Y, 220, 58), "CONTINUE", "gold", 26, self.try_next)
        self.buttons = [self.btn_back, self.btn_auto, self.btn_next]

    # ---- geometry ----
    def y0(self):
        if PORTRAIT:
            return 214
        total = self.draft.n * self.ROW_H
        return 214 + max(0, (390 - total) // 2)

    def row_rect(self, i):
        return pygame.Rect(CX - self.PANEL_W // 2, self.y0() + i * self.ROW_H, self.PANEL_W, self.ROW_H - 10)

    def tile_rect(self, i, c):
        r = self.row_rect(i)
        if PORTRAIT:                                  # tiles in a row under the player's name
            x0 = r.x + (r.w - (4 * self.TILE_W + 3 * self.TILE_GAP)) // 2
            return pygame.Rect(x0 + c * (self.TILE_W + self.TILE_GAP), r.bottom - 14 - self.TILE_H, self.TILE_W, self.TILE_H)
        x0 = r.right - 20 - (4 * self.TILE_W + 3 * self.TILE_GAP)
        return pygame.Rect(x0 + c * (self.TILE_W + self.TILE_GAP), r.centery - self.TILE_H // 2, self.TILE_W, self.TILE_H)

    # ---- actions ----
    def say(self, text, secs=2.6):
        self.notice = (text, self.t + secs)

    def do_auto(self):
        self.click_sound()
        self.draft.auto_assign()

    def try_next(self):
        if not self.draft.colours_complete:
            self.audio.play("shield_block", .4)
            self.say("Choose a colour for every player first")
            return
        self.click_sound()
        self.on_next()

    def pick(self, i, c):
        d = self.draft
        reason = d.block_reason(i, c)
        if reason:
            self.deny[(i, c)] = .3
            self.audio.play("shield_block", .35)
            self.say(reason + " — pick another colour")
            return
        other_before = d.colours[1 - i] if d.n == 2 else None
        d.pick_colour(i, c)
        self.click_sound()
        if d.n == 2 and d.colours[i] is not None and other_before is not None and d.colours[1 - i] != other_before:
            j = 1 - i
            self.say(f"{clean_name(d.names[j], j)} now plays {COLOUR_NAMES[d.colours[j]]} (the opposite corner)")

    def handle_event(self, e):
        for b in self.buttons:
            b.handle(e)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i in range(self.draft.n):
                for c in range(4):
                    if self.tile_rect(i, c).collidepoint(e.pos):
                        self.pick(i, c)
                        return

    def update(self, dt):
        super().update(dt)
        for k in list(self.deny):
            self.deny[k] -= dt
            if self.deny[k] <= 0:
                del self.deny[k]
        m = pygame.mouse.get_pos()
        self.hover_tile = next(((i, c) for i in range(self.draft.n) for c in range(4) if self.tile_rect(i, c).collidepoint(m)), None)
        self.hover = approach(self.hover, 1.0 if self.hover_tile else 0.0, 14, dt)

    # ---- draw ----
    def draw_tile(self, surf, i, c):
        d = self.draft
        r = self.tile_rect(i, c)
        sel = d.colours[i] == c
        blocked = d.block_reason(i, c) is not None
        hov = self.hover_tile == (i, c) and not blocked
        col = PLAYER_COLORS[c]
        dx = math.sin(self.deny.get((i, c), 0) * 60) * 4 if (i, c) in self.deny else 0
        r = r.move(dx, -3 if hov else 0)
        if sel:
            draw_glow(surf, r.center, 100, col, .45)
        base = (36, 38, 58) if blocked else lerp_color(shade(col, .38), shade(col, .7), 1.0 if (sel or hov) else 0.0)
        pygame.draw.rect(surf, base, r, border_radius=14)
        pygame.draw.rect(surf, GOLD_LIGHT if sel else (GOLD if hov else (shade(col, .6) if not blocked else (70, 72, 92))),
                         r, 4 if sel else 2, border_radius=14)
        spr = token_sprite(GREY if blocked else col, 15)
        surf.blit(spr, spr.get_rect(center=(r.x + 30, r.centery)))
        draw_text(surf, COLOUR_NAMES[c], 20, (120, 122, 142) if blocked else WHITE, (r.x + 54, r.centery - (8 if blocked else 0)), "midleft")
        if blocked:
            draw_lock(surf, r.x + 62, r.centery + 14, 6, (140, 142, 160))
            draw_text(surf, "TAKEN", 11, (140, 142, 160), (r.x + 74, r.centery + 15), "midleft")
        elif sel:
            bx, by = r.right - 12, r.y + 12
            pygame.draw.circle(surf, GOLD_LIGHT, (bx, by), 9)
            pygame.draw.lines(surf, INK, False, [(bx - 4, by), (bx - 1, by + 3), (bx + 4, by - 3)], 2)

    def draw(self, surf):
        self.draw_frame(surf)
        d = self.draft
        for i in range(d.n):
            r = self.row_rect(i)
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (14, 16, 40, 205), panel.get_rect(), border_radius=18)
            surf.blit(panel, r.topleft)
            chosen = d.colours[i]
            pygame.draw.rect(surf, PLAYER_COLORS[chosen] if chosen is not None else (70, 76, 120), r, 3 if chosen is not None else 2, border_radius=18)
            spr = token_sprite(PLAYER_COLORS[chosen] if chosen is not None else GREY, 17)
            hy = r.y + 34 if PORTRAIT else r.centery
            surf.blit(spr, spr.get_rect(center=(r.x + 38, hy)))
            nm = clean_name(d.names[i], i)
            if PORTRAIT:
                draw_text_fit(surf, nm.upper(), 24, WHITE, (r.x + 72, hy), 330, "midleft", min_size=12)
                draw_text(surf, COLOUR_NAMES[chosen] if chosen is not None else "no colour yet", 16,
                          PLAYER_COLORS[chosen] if chosen is not None else (150, 156, 190), (r.right - 20, hy), "midright")
            else:
                draw_text_fit(surf, nm.upper(), 24, WHITE, (r.x + 72, r.centery - 10), 200, "midleft", min_size=12)
                draw_text(surf, COLOUR_NAMES[chosen] if chosen is not None else "no colour yet", 14,
                          PLAYER_COLORS[chosen] if chosen is not None else (150, 156, 190), (r.x + 72, r.centery + 14), "midleft")
            for c in range(4):
                self.draw_tile(surf, i, c)
        # status / hint / notice line
        ny = (self.y0() + d.n * self.ROW_H + 8) if PORTRAIT else 598
        if self.notice[1] > self.t:
            draw_text_fit(surf, self.notice[0], 17, (255, 190, 120), (CX, ny), WIDTH - 30)
        elif d.colours_complete:
            draw_text(surf, "All set — press CONTINUE", 17, (130, 220, 150), (CX, ny))
        else:
            draw_text_fit(surf, "Tap a colour for each player. Tap your own colour again to change it.", 16, (150, 158, 195), (CX, ny), WIDTH - 30)
        if d.n == 2:
            draw_text_fit(surf, "2 players always sit on opposite corners: Red-Blue or Green-Yellow", 14, (130, 138, 178), (CX, ny + 26), WIDTH - 30)
        self.btn_next.enabled = d.colours_complete
        for b in self.buttons:
            b.draw(surf)


# ========================================================================== review
class ReviewScreen(_Step):
    ROW_H = 76

    def __init__(self, draft, on_back, on_edit_names, on_start):
        super().__init__(3, "REVIEW", "Check the line-up, then start the game")
        self.draft = draft
        if PORTRAIT:
            self.btn_back = Button((24, BTN_Y, 170, 58), "BACK", "slate", 24, lambda: (self.click_sound(), on_back()))
            self.btn_names = Button((206, BTN_Y, 220, 58), "EDIT NAMES", "violet", 22, lambda: (self.click_sound(), on_edit_names()))
            self.btn_start = Button((438, BTN_Y, 258, 58), "START GAME", "gold", 26, lambda: (self.click_sound(), on_start()))
        else:
            self.btn_back = Button((CX - 420, BTN_Y, 220, 58), "BACK", "slate", 26, lambda: (self.click_sound(), on_back()))
            self.btn_names = Button((CX - 170, BTN_Y, 260, 58), "EDIT NAMES", "violet", 24, lambda: (self.click_sound(), on_edit_names()))
            self.btn_start = Button((CX + 140, BTN_Y, 280, 58), "START GAME", "gold", 28, lambda: (self.click_sound(), on_start()))
        self.buttons = [self.btn_back, self.btn_names, self.btn_start]

    def handle_event(self, e):
        for b in self.buttons:
            b.handle(e)

    def draw(self, surf):
        self.draw_frame(surf)
        d = self.draft
        names = d.display_names()
        players = sorted(range(d.n), key=lambda i: d.colours[i] if d.colours[i] is not None else 9)   # clockwise board order
        panel = pygame.Rect(CX - (340 if PORTRAIT else 380), 240 if PORTRAIT else 214, 680 if PORTRAIT else 760, d.n * self.ROW_H + 70)
        bg = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (14, 16, 40, 215), bg.get_rect(), border_radius=22)
        surf.blit(bg, panel.topleft)
        pygame.draw.rect(surf, GOLD_DARK, panel, 2, border_radius=22)
        draw_text(surf, f"{d.n} PLAYERS  •  TURN ORDER GOES CLOCKWISE AROUND THE BOARD", 14, (150, 158, 195), (CX, panel.y + 24))
        for k, i in enumerate(players):
            c = d.colours[i]
            y = panel.y + 56 + k * self.ROW_H
            row = pygame.Rect(panel.x + 18, y, panel.w - 36, self.ROW_H - 10)
            col = PLAYER_COLORS[c]
            pygame.draw.rect(surf, shade(col, .28), row, border_radius=16)
            pygame.draw.rect(surf, col, row, 3, border_radius=16)
            draw_text(surf, str(k + 1), 26, GOLD_LIGHT, (row.x + 28, row.centery))
            for t in range(4):
                spr = token_sprite(col, 11)
                surf.blit(spr, spr.get_rect(center=(row.x + 74 + t * 24, row.centery)))
            draw_text_fit(surf, names[i].upper(), 28, WHITE, (row.x + 190, row.centery - 8), 270, "midleft", shadow=(0, 0, 0), min_size=14)
            draw_text(surf, f"PLAYER {i + 1}", 12, (170, 176, 205), (row.x + 190, row.centery + 16), "midleft")
            draw_text(surf, COLOUR_NAMES[c].upper(), 22, col, (row.right - 28, row.centery - 8), "midright", shadow=(0, 0, 0))
            draw_text(surf, f"{SEAT_NAMES[c]} corner of the board", 13, (170, 176, 205), (row.right - 28, row.centery + 15), "midright")
        draw_text(surf, "The player who goes first is chosen at random.", 16, GOLD_LIGHT, (CX, panel.bottom + 26))
        for b in self.buttons:
            b.draw(surf)
