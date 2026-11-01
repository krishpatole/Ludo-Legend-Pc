"""Start-up warm-up: build every expensive cached surface (board, cards, dice, tokens, glows, text, game scene)
behind a LOADING screen, so nothing is generated in the middle of a menu animation or when START GAME is pressed.

Each step is tiny and wrapped in try/except: a failed warm-up step can never stop the game from starting.
"""
from __future__ import annotations
import math
import pygame
from config.settings import *


def _steps(app):
    from game.setup import GameSetup
    from ui.board_view import board_surface, token_sprite
    from ui.dice_view import die_face
    from ui.cards import card_face
    from powers.power_card import PowerType
    from ui.game_ui import GameScene
    from ui.menu import MenuScreen, OptionsScreen
    from ui.player_selection import PlayerSelectScreen
    from utils.helpers import get_background, crown_surface, draw_glow
    scratch = pygame.Surface((WIDTH, HEIGHT))

    def background():
        get_background()

    for subset in ((0, 2), (1, 3), (0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3), (0, 1, 2, 3)):
        yield lambda s=subset: board_surface(s)
    yield background
    yield lambda: [card_face(k, CARD_W, CARD_H) for k in PowerType]
    yield lambda: [die_face(v, sz) for v in range(1, 7) for sz in (56, 62, 68)]
    yield lambda: [token_sprite(c, r) for c in PLAYER_COLORS for r in (9, 11, 13, 15, 17, TOKEN_R)]
    yield lambda: [crown_surface(w) for w in (18, 44, 54, 60, 110, 112)]
    yield lambda: [draw_glow(scratch, (300, 300), r, c, 1.0) for c in PLAYER_COLORS for r in (20, 24, 52, 62, 100, 170)]
    yield lambda: MenuScreen(lambda a: None).draw(scratch)
    yield lambda: OptionsScreen(lambda: None, lambda: None).draw(scratch)
    yield lambda: PlayerSelectScreen(lambda n: None, lambda: None).draw(scratch)
    for n in (4, 2):                                   # building + drawing one real game scene warms everything it uses
        box = []
        yield lambda n=n, box=box: box.append(GameScene(GameSetup.default(n), lambda a: None))
        yield lambda box=box: (box[0].update(1 / 30), box[0].draw(scratch))
        yield lambda box=box: (box[0].update(1 / 30), box[0].draw(scratch))


class Warmup:
    """Runs the steps a few milliseconds per frame and draws a progress bar."""
    BUDGET = 0.030                                      # seconds of work per frame

    def __init__(self, app):
        self.steps = list(_steps(app))
        self.total = max(1, len(self.steps))
        self.done = 0
        self.t = 0.0

    @property
    def finished(self):
        return self.done >= self.total

    def update(self, dt):
        import time
        self.t += dt
        start = time.perf_counter()
        while self.done < self.total and time.perf_counter() - start < self.BUDGET:
            try:
                self.steps[self.done]()
            except Exception as e:                      # never block the game on a cache step
                print("[warmup] skipped a step:", e)
            self.done += 1

    def handle_event(self, e):
        pass

    def draw(self, surf):
        from utils.helpers import draw_text, gradient_surface
        surf.fill((14, 14, 34))
        cx, cy = WIDTH // 2, HEIGHT // 2
        draw_text(surf, TITLE, 56 if PORTRAIT else 72, GOLD_LIGHT, (cx, cy - 70), shadow=(0, 0, 0))
        w = min(420, WIDTH - 120)
        bar = pygame.Rect(0, 0, w, 16)
        bar.center = (cx, cy + 10)
        pygame.draw.rect(surf, (40, 44, 86), bar, border_radius=8)
        fill = bar.copy()
        fill.w = max(16, int(bar.w * self.done / self.total))
        pygame.draw.rect(surf, GOLD, fill, border_radius=8)
        pygame.draw.rect(surf, GOLD_DARK, bar, 2, border_radius=8)
        draw_text(surf, "LOADING" + "." * (int(self.t * 3) % 4), 22, (170, 178, 215), (cx, cy + 50))
