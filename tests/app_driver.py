"""Drive the REAL App (window scaling, input mapping, fades, scene switching) with synthetic input.

Used by the UI tests: tap(), type_text(), press(), and start_game_via_ui() which walks the whole
Main Menu -> Player Count -> Names -> Colours -> Review -> Start Game flow exactly like a user.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_harness import *            # sets SDL dummy drivers, pygame, SCREEN, move_mouse, SHOTS, ...
from game.app import App
from ui.game_ui import GameScene

DT = 1 / 60


def to_window(app, pos):
    """Canvas point -> where the OS would report it in the (scaled, letter-boxed) window."""
    k, (ox, oy), _ = app._viewport()
    return int(pos[0] * k + ox), int(pos[1] * k + oy)


def tap(app, pos, frames=3):
    wp = to_window(app, pos)
    move_mouse(wp)
    app.frame(DT, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=wp, button=1)])
    app.frame(DT, [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=wp, button=1)])
    for _ in range(frames):
        app.frame(DT)


def idle(app, secs):
    for _ in range(int(secs * 60)):
        app.frame(DT)


def until(app, pred, limit=20.0):
    for _ in range(int(limit * 60)):
        if pred():
            return True
        app.frame(DT)
    return pred()


def type_text(app, text):
    """Type like a keyboard / on-screen keyboard: one TEXTINPUT event per character."""
    for ch in text:
        app.frame(DT, [pygame.event.Event(pygame.TEXTINPUT, text=ch)])


def press(app, key, mod=0):
    app.frame(DT, [pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode="", scancode=0)])
    app.frame(DT, [pygame.event.Event(pygame.KEYUP, key=key, mod=mod)])


def snap(app, name):
    app.frame(DT)
    pygame.image.save(app.screen, os.path.join(SHOTS, name + ".png"))


def center(rect):
    return (rect.centerx, rect.centery)


def new_app():
    app = App()
    idle(app, .5)
    return app


def open_setup(app):
    """Menu -> PLAY (player-count screen)."""
    tap(app, center(app.scene.buttons[0].rect))
    assert until(app, lambda: app.state == S.PLAYER_SELECTION, 3), app.state
    idle(app, .4)


def choose_count(app, n):
    rect = next(c["rect"] for c in app.scene.cards if c["n"] == n)
    tap(app, center(rect), 0)
    assert until(app, lambda: app.state == S.PLAYER_NAMES, 3), app.state
    idle(app, .4)


def enter_names(app, names):
    """names: list of str ('' keeps the default)."""
    for i, nm in enumerate(names):
        tap(app, center(app.scene.field_rect(i)), 1)
        type_text(app, nm)


def pick_colours(app, colours):
    """colours: list of colour ids, one per player slot (taps the real tiles)."""
    sc = app.scene
    assert app.state == S.COLOR_SELECTION
    for i, c in enumerate(colours):
        if sc.draft.colours[i] != c:
            tap(app, center(sc.tile_rect(i, c)), 1)
    return sc.draft.colours[:len(colours)]


def start_game_via_ui(app, n, names=None, colours=None, wait_turn=True):
    """Full user flow from the main menu. Returns the running GameScene."""
    assert app.state == S.MENU
    open_setup(app)
    choose_count(app, n)
    enter_names(app, names or [""] * n)
    tap(app, center(app.scene.btn_next.rect), 0)
    assert until(app, lambda: app.state == S.COLOR_SELECTION, 3), app.state
    idle(app, .4)
    if colours is None:
        tap(app, center(app.scene.btn_auto.rect), 1)
    else:
        pick_colours(app, colours)
    tap(app, center(app.scene.btn_next.rect), 0)
    assert until(app, lambda: app.state == S.SETUP_REVIEW, 3), app.state
    idle(app, .4)
    tap(app, center(app.scene.btn_start.rect), 0)
    assert until(app, lambda: isinstance(app.scene, GameScene), 4), "game did not start"
    if wait_turn:
        assert until(app, lambda: app.scene.state == S.PLAYER_TURN, 12)
    return app.scene


def place(sc, colour, idx, step):
    """Put a token on an exact step (model + its on-screen view), like a mid-game position."""
    from game.board import token_px
    tk = sc.match.players[colour].tokens[idx]
    tk.step = step
    v = sc.views[(colour, idx)]
    v.x, v.y = token_px(colour, step, idx)
    v.cell_key = v.logic_key()


def tok_pos(sc, colour, idx):
    v = sc.views[(colour, idx)]
    return (int(v.pos[0]), int(v.pos[1]))


def record_banners(sc):
    """Wrap sc.banner so a test can see which banner texts were shown."""
    log = []
    orig = sc.banner

    def spy(lines, *a, **k):
        log.append(lines[0])
        return orig(lines, *a, **k)
    sc.banner = spy
    return log


def settle(sc, app=None, limit=40):
    """Advance until the scene waits for input on a PLAYER_TURN."""
    f = (lambda: app.frame(DT)) if app else (lambda: sc.update(DT))
    for _ in range(int(limit * 60)):
        if sc.state == S.PLAYER_TURN:
            return True
        f()
    return False
