"""Phone / portrait layout (720x1280): nothing overlaps, everything is inside the screen and reachable by touch.

This suite forces the portrait profile itself, so it runs in the normal `python run_tests.py` too.
"""
import os, sys
os.environ["LUDO_LAYOUT"] = "portrait"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_driver import *
from config.settings import PORTRAIT
from ui import layout as L

SCREEN_RECT = pygame.Rect(0, 0, WIDTH, HEIGHT)


def test_profile_is_portrait():
    assert PORTRAIT and (WIDTH, HEIGHT) == (720, 1280)
    board = pygame.Rect(BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE)
    assert SCREEN_RECT.contains(board)
    print("ok profile", board)


def test_game_layout_has_no_overlaps():
    board = pygame.Rect(BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE)
    items = {"HUD": L.HUD_RECT, "MENU": L.MENU_BTN, "BOARD": board}
    for s in range(4):
        items[f"zone{s}"] = L.zone_rect(s)
        c = L.dice_center(s)
        items[f"dice{s}"] = pygame.Rect(0, 0, L.DICE_SIZE, L.DICE_SIZE); items[f"dice{s}"].center = c
    names = list(items)
    for n, r in items.items():
        assert SCREEN_RECT.contains(r), (n, r)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert not items[a].colliderect(items[b]), (a, b, items[a], items[b])
    print("ok game layout: no overlaps among", len(items), "elements")


def test_menu_and_option_screens_fit():
    app = new_app()
    for b in app.scene.buttons: assert SCREEN_RECT.contains(b.rect), b.rect
    open_setup(app)
    for c in app.scene.cards: assert SCREEN_RECT.contains(c["rect"])
    rs = [c["rect"] for c in app.scene.cards] + [app.scene.btn_back.rect]
    for i, a in enumerate(rs):
        for b in rs[i + 1:]: assert not a.colliderect(b)
    print("ok count screen")


def test_setup_screens_fit_for_every_count():
    for n in (2, 3, 4):
        app = new_app(); open_setup(app); choose_count(app, n)
        sc = app.scene
        rects = [sc.field_rect(i) for i in range(n)] + [b.rect for b in sc.buttons]
        for r in rects: assert SCREEN_RECT.contains(r), r
        for i, a in enumerate(rects):
            for b in rects[i + 1:]: assert not a.colliderect(b), (a, b)
        enter_names(app, ["Krishnamurthy Patole", "B", "Zoe Quinn", "Dev"][:n])
        tap(app, center(sc.btn_next.rect), 0); assert until(app, lambda: app.state == S.COLOR_SELECTION, 3)
        idle(app, .4); sc = app.scene
        tiles = [sc.tile_rect(i, c) for i in range(n) for c in range(4)]
        rects = tiles + [b.rect for b in sc.buttons]
        for r in rects: assert SCREEN_RECT.contains(r), r
        for i, a in enumerate(rects):
            for b in rects[i + 1:]: assert not a.colliderect(b), (a, b)
        assert max(sc.row_rect(i).bottom for i in range(n)) < sc.btn_back.rect.y - 20
        cols = {2: [3, 1], 3: [2, 0, 3], 4: [1, 2, 3, 0]}[n]
        pick_colours(app, cols); assert sc.draft.colours[:n] == cols
        tap(app, center(sc.btn_next.rect), 0); assert until(app, lambda: app.state == S.SETUP_REVIEW, 3); idle(app, .4)
        for b in app.scene.buttons: assert SCREEN_RECT.contains(b.rect)
        bs = [b.rect for b in app.scene.buttons]
        for i, a in enumerate(bs):
            for b in bs[i + 1:]: assert not a.colliderect(b)
        print(f"ok setup screens {n} players")


def test_full_game_start_and_touch_roll_and_victory():
    app = new_app()
    sc = start_game_via_ui(app, 4, ["Asha", "Ben", "Zoe", "Dev"], [1, 2, 3, 0])
    assert (WIDTH, HEIGHT) == (720, 1280) and sc.state == S.PLAYER_TURN
    cur = sc.cur
    # tap the current player's die with a real touch and a roll must start
    tap(app, L.dice_center(cur), 1)
    assert until(app, lambda: sc.state != S.PLAYER_TURN, 3), sc.state
    for card_seat in sc.order:
        for i in range(len(sc.hands[card_seat])):
            x, y = L.card_slot(card_seat, i, len(sc.hands[card_seat]))
            assert SCREEN_RECT.collidepoint(x, y)
    # victory overlay buttons fit and are tappable
    from ui.victory import VictoryOverlay
    v = VictoryOverlay(0, PLAYER_COLORS[0], lambda a: None, "Asha")
    assert SCREEN_RECT.contains(v.btn_again.rect) and SCREEN_RECT.contains(v.btn_menu.rect)
    assert not v.btn_again.rect.colliderect(v.btn_menu.rect)
    print("ok game start / touch roll / victory buttons")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"): fn()
    print("PORTRAIT TESTS PASSED")
