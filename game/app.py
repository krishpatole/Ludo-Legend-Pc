"""App: owns the window, the scene stack and the top-level state (MENU / PLAYER_SELECTION / OPTIONS / in-game)."""
from __future__ import annotations
import os, sys
import pygame
from config.settings import WIDTH, HEIGHT, FPS, TITLE, SETTINGS
from audio.audio_manager import get_audio
from game.states import GameState as S
from game.setup import GameSetup, SetupDraft, SetupError
from ui.menu import MenuScreen, OptionsScreen
from ui.player_selection import PlayerSelectScreen
from ui.setup_screens import NamesScreen, ColoursScreen, ReviewScreen
from ui.game_ui import GameScene
from utils.helpers import approach


class App:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(TITLE)
        # The game always renders to a fixed 1366x768 canvas which is scaled (letter-boxed) to the
        # real window / phone screen. Mouse + touch positions are mapped back to canvas coordinates.
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self.window = self._make_window()
        self._raw_mouse = pygame.mouse.get_pos
        self._touch_pos = None          # last finger position (window pixels) while touch is the active input
        pygame.mouse.get_pos = self.canvas_mouse
        self.fullscreen = False
        self.clock = pygame.time.Clock()
        self.audio = get_audio()
        self.audio.apply_settings()
        self.scene = None
        self.scene_state = S.MENU
        self.draft = SetupDraft()          # what the setup screens are editing
        self.setup: GameSetup | None = None  # the validated setup of the running / last match
        self.fade = 1.0            # 1 = black. Scenes fade in from black.
        self.pending = None
        self.running = True
        self.goto(S.MENU, instant=True)

    # ---- window / scaling -------------------------------------------------
    @staticmethod
    def _desktop_size():
        """Size of the desktop (NOT of the current window, which Info() would report once a window exists)."""
        try:
            sizes = pygame.display.get_desktop_sizes()
            if sizes and sizes[0][0] > 0 and sizes[0][1] > 0:
                return sizes[0]
        except Exception:
            pass
        info = pygame.display.Info()
        return (info.current_w or WIDTH, info.current_h or HEIGHT)

    def _make_window(self, size=None):
        if size is None:
            sw, sh = self._desktop_size()
            # fit inside the desktop (leave room for the title bar / taskbar); never upscale beyond 1366x768
            k = min(1.0, (sw - 80) / WIDTH, (sh - 120) / HEIGHT)
            k = max(k, 0.35)
            size = (WIDTH, HEIGHT) if k >= 1 else (int(WIDTH * k), int(HEIGHT * k))
        flags = pygame.RESIZABLE
        if sys.platform == "android" or os.environ.get("ANDROID_ARGUMENT"):
            flags, size = pygame.FULLSCREEN, (0, 0)
        return pygame.display.set_mode(size, flags)

    def _viewport(self):
        ww, wh = self.window.get_size()
        ww, wh = max(1, ww), max(1, wh)               # a minimised window can report 0x0
        k = min(ww / WIDTH, wh / HEIGHT)
        w, h = round(WIDTH * k), round(HEIGHT * k)
        return k, ((ww - w) // 2, (wh - h) // 2), (w, h)

    def to_canvas(self, pos):
        k, (ox, oy), _ = self._viewport()
        return int((pos[0] - ox) / k), int((pos[1] - oy) / k)

    def canvas_mouse(self):
        return self.to_canvas(self._touch_pos if self._touch_pos is not None else self._raw_mouse())

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = self._make_window()

    def present(self):
        if pygame.display.get_surface() is not None:
            self.window = pygame.display.get_surface()    # always the live surface (resize / fullscreen)
        k, off, size = self._viewport()
        if size[0] < 2 or size[1] < 2:
            return                                         # nothing sensible to draw while minimised
        self.window.fill((0, 0, 0))
        if size == (WIDTH, HEIGHT):
            self.window.blit(self.screen, off)
        else:
            self.window.blit(pygame.transform.smoothscale(self.screen, size), off)
        pygame.display.flip()

    # ---- scene switching (with a quick fade through black) ----------------
    def goto(self, state: S, instant=False, n=None):
        if n is not None and state == S.DETERMINING_FIRST_PLAYER:
            self.setup = GameSetup.default(n)          # shortcut used by tests / tools: skip the setup screens
        if instant:
            self._build(state)
        else:
            self.pending = (state, n)

    def _build(self, state, n=None):
        old = self.scene
        if old is not None and hasattr(old, "close"):
            old.close()                                # e.g. stop text input when leaving the names screen
        self.scene_state = state
        d = self.draft
        if state == S.MENU:
            self.scene = MenuScreen(self.on_menu)
        elif state == S.OPTIONS:
            self.scene = OptionsScreen(lambda: self.goto(S.MENU), self.audio.apply_settings)
        elif state == S.PLAYER_SELECTION:
            self.scene = PlayerSelectScreen(self.on_count_chosen, lambda: self.goto(S.MENU))
        elif state == S.PLAYER_NAMES:
            self.scene = NamesScreen(d, lambda: self.goto(S.PLAYER_SELECTION), lambda: self.goto(S.COLOR_SELECTION))
        elif state == S.COLOR_SELECTION:
            self.scene = ColoursScreen(d, lambda: self.goto(S.PLAYER_NAMES), lambda: self.goto(S.SETUP_REVIEW))
        elif state == S.SETUP_REVIEW:
            self.scene = ReviewScreen(d, lambda: self.goto(S.COLOR_SELECTION), lambda: self.goto(S.PLAYER_NAMES), self.start_game)
        elif state == S.DETERMINING_FIRST_PLAYER:
            if self.setup is None:
                self.setup = GameSetup.default(4)
            self.scene = GameScene(self.setup, self.on_game_exit)       # a brand-new Match: nothing carries over

    @property
    def n_players(self) -> int:
        return self.setup.n if self.setup else self.draft.n

    def on_count_chosen(self, n: int):
        self.draft.set_count(n)
        self.goto(S.PLAYER_NAMES)

    def start_game(self):
        if self.pending:
            return                                     # ignore repeated clicks during the fade
        try:
            self.setup = self.draft.build()            # validates names + unique colours (+ opposite corners for 2)
        except SetupError:
            self.goto(S.COLOR_SELECTION)               # should not happen: the screens already enforce the rules
            return
        self.goto(S.DETERMINING_FIRST_PLAYER)

    @property
    def state(self) -> S:
        """Top-level state; while a match is running it mirrors the match's own state."""
        return self.scene.state if isinstance(self.scene, GameScene) else self.scene_state

    def on_menu(self, action):
        if action == "play":
            self.goto(S.PLAYER_SELECTION)
        elif action == "options":
            self.goto(S.OPTIONS)
        elif action == "exit":
            self.running = False

    def on_game_exit(self, what):
        if self.pending:
            return                                   # ignore repeated clicks during the fade
        self.audio.play("click")
        self.goto(S.DETERMINING_FIRST_PLAYER) if what == "again" else self.goto(S.MENU)    # same players, fresh match

    # ---- main loop ----------------------------------------------------------
    _FINGER = {pygame.FINGERDOWN: pygame.MOUSEBUTTONDOWN, pygame.FINGERUP: pygame.MOUSEBUTTONUP,
               pygame.FINGERMOTION: pygame.MOUSEMOTION}

    def _translate_touch(self, e):
        """Finger events (x, y in 0..1) -> the equivalent left-button mouse event in window pixels.
        Mouse events that SDL itself emulates from a touch (event.touch == True) are dropped so a
        single tap is never delivered twice."""
        if e.type in self._FINGER:
            ww, wh = self.window.get_size()
            pos = (int(e.x * ww), int(e.y * wh))
            self._touch_pos = pos
            kind = self._FINGER[e.type]
            if kind == pygame.MOUSEMOTION:
                return pygame.event.Event(kind, pos=pos, rel=(0, 0), buttons=(1, 0, 0), touch=True, synthetic=True)
            return pygame.event.Event(kind, pos=pos, button=1, touch=True, synthetic=True)
        if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            if getattr(e, "touch", False) and not getattr(e, "synthetic", False):
                return None                              # SDL's emulation of a finger we already handled
            if not getattr(e, "touch", False):
                self._touch_pos = None                   # a real mouse is in use again
        return e

    BACK_TARGET = {S.OPTIONS: S.MENU, S.PLAYER_SELECTION: S.MENU, S.PLAYER_NAMES: S.PLAYER_SELECTION,
                   S.COLOR_SELECTION: S.PLAYER_NAMES, S.SETUP_REVIEW: S.COLOR_SELECTION}

    def handle_events(self, events) -> None:
        for e in events:
            e = self._translate_touch(e)
            if e is None:
                continue
            if hasattr(e, "pos") and e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                e = pygame.event.Event(e.type, {**e.dict, "pos": self.to_canvas(e.pos)})
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, getattr(pygame, "K_AC_BACK", -1)):
                if isinstance(self.scene, GameScene):
                    self.on_game_exit("menu")
                elif self.scene_state in self.BACK_TARGET and not self.pending:
                    self.goto(self.BACK_TARGET[self.scene_state])
            elif not self.pending:
                self.scene.handle_event(e)

    def frame(self, dt: float, events=()) -> None:
        """One full iteration: input -> update -> fade/scene switch -> draw -> present."""
        self.handle_events(events)
        self.scene.update(dt)
        if self.pending:
            self.fade = min(1.0, self.fade + dt * 6)
            if self.fade >= 1.0:
                st, n = self.pending
                self.pending = None
                self._build(st, n)
        else:
            self.fade = max(0.0, self.fade - dt * 4)
        self.scene.draw(self.screen)
        if self.fade > 0.01:
            veil = pygame.Surface((WIDTH, HEIGHT))
            veil.set_alpha(int(255 * self.fade))
            self.screen.blit(veil, (0, 0))
        self.present()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.frame(dt, pygame.event.get())
        pygame.quit()
