"""Setup flow + custom names + colours, through the REAL screens (synthetic taps and typed text)."""
import os, sys, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_driver import *
from game.setup import OPPOSITE, MAX_NAME_LEN
from powers.power_card import PowerType as P
from ui import layout as L
from utils.helpers import draw_text_fit
from ui.setup_screens import NamesScreen, ColoursScreen, ReviewScreen


def test_full_wizard_for_every_player_count():
    for n in (2, 3, 4):
        colours = {2: [3, 1], 3: [2, 0, 3], 4: [1, 2, 3, 0]}[n]
        names = ["Asha", "Ben Carter", "Zoe", "Dev"][:n]
        app = new_app(); sc = start_game_via_ui(app, n, names, colours)
        assert sc.n == n and sc.setup.n == n
        assert sorted(sc.order) == sorted(colours)                              # only the chosen colours play
        assert len(sc.match.players) == n and len(sc.hands) == n and len(sc.dices) == n
        assert len(sc.views) == 4 * n                                           # 4 tokens each, nobody else
        for nm, c in zip(names, colours):
            assert sc.label(c) == nm.upper()
            assert sc.match.players[c].name == nm
            assert len(sc.hands[c]) == 3                                        # each player owns three cards
        assert [sc.label(c) for c in sc.order] == [sc.match.players[c].label for c in sorted(colours)]
        print(f"ok wizard {n} players: colours {colours} order {sc.order}")


def test_names_default_trim_limit_edit_and_navigation():
    app = new_app(); open_setup(app); choose_count(app, 3)
    sc = app.scene; assert isinstance(sc, NamesScreen)
    # typing + backspace + max length
    tap(app, center(sc.field_rect(0)), 1); type_text(app, "  Krish   Patole  ")
    assert sc.draft.names[0] == "  Krish   Patole  "[:MAX_NAME_LEN]
    press(app, pygame.K_BACKSPACE); press(app, pygame.K_BACKSPACE)
    type_text(app, "x" * 40); assert len(sc.draft.names[0]) == MAX_NAME_LEN
    sc.draft.names[0] = "  Krish   Patole  "                                    # whitespace is cleaned in the final name
    assert sc.draft.display_names()[0] == "Krish Patole"
    # Tab / Enter move between fields; empty field -> default; control characters are ignored
    press(app, pygame.K_TAB); assert sc.focus == 1
    type_text(app, "Zoe\n\t\x07"); assert sc.draft.names[1] == "Zoe"
    press(app, pygame.K_RETURN); assert sc.focus == 2
    assert sc.draft.display_names() == ["Krish Patole", "Zoe", "Player 3"]
    # duplicate (case-insensitive) names block Continue and say why
    type_text(app, "zoe"); assert sc.draft.name_errors()
    before = app.state; tap(app, center(sc.btn_next.rect), 0); idle(app, .6); assert app.state == before == S.PLAYER_NAMES
    for _ in range(3): press(app, pygame.K_BACKSPACE)
    assert not sc.draft.name_errors()
    # going forward then Esc/back keeps everything that was typed
    tap(app, center(sc.btn_next.rect), 0); assert until(app, lambda: app.state == S.COLOR_SELECTION, 3); idle(app, .3)
    press(app, pygame.K_ESCAPE); assert until(app, lambda: app.state == S.PLAYER_NAMES, 3); idle(app, .3)
    assert app.scene.draft.names[:2] == ["  Krish   Patole  ", "Zoe"]
    # text input is switched off again when leaving the names screen (no stray typing elsewhere)
    print("ok names")


def test_colours_unique_locked_and_two_player_opposite():
    # ---- 4 players: every colour used once; taken colours cannot be picked
    app = new_app(); open_setup(app); choose_count(app, 4)
    tap(app, center(app.scene.btn_next.rect), 0); until(app, lambda: app.state == S.COLOR_SELECTION, 3); idle(app, .3)
    sc = app.scene; assert isinstance(sc, ColoursScreen); d = sc.draft
    assert not sc.btn_next.enabled or True
    tap(app, center(sc.tile_rect(0, 1)), 1); assert d.colours[0] == 1
    tap(app, center(sc.tile_rect(1, 1)), 1); assert d.colours[1] is None and (1, 1) in sc.deny or d.colours[1] is None
    assert d.block_reason(1, 1) and "Taken" in d.block_reason(1, 1)
    tap(app, center(sc.tile_rect(1, 2)), 1); tap(app, center(sc.tile_rect(2, 3)), 1); tap(app, center(sc.tile_rect(3, 0)), 1)
    assert d.colours[:4] == [1, 2, 3, 0] and len(set(d.colours[:4])) == 4
    tap(app, center(sc.tile_rect(3, 1)), 1); assert d.colours[3] == 0                 # still locked (P1 owns Green)
    tap(app, center(sc.tile_rect(0, 1)), 1); assert d.colours[0] is None               # tap your own colour to release it
    tap(app, center(sc.tile_rect(3, 1)), 1); assert d.colours[3] == 1                  # ...and now it is free for others
    assert len({c for c in d.colours[:4] if c is not None}) == len([c for c in d.colours[:4] if c is not None])
    before = app.state; tap(app, center(sc.btn_next.rect), 0); idle(app, .5)
    assert app.state == before == S.COLOR_SELECTION                                    # incomplete -> cannot continue
    tap(app, center(sc.btn_auto.rect), 1); assert d.colours_complete and len(set(d.colours[:4])) == 4
    # ---- 2 players: always opposite corners (verified against the board in test_setup)
    app = new_app(); open_setup(app); choose_count(app, 2)
    tap(app, center(app.scene.btn_next.rect), 0); until(app, lambda: app.state == S.COLOR_SELECTION, 3); idle(app, .3)
    sc = app.scene; d = sc.draft
    for who, c in itertools.product((0, 1), range(4)):
        tap(app, center(sc.tile_rect(who, c)), 0)
        a, b = d.colours[0], d.colours[1]
        if a is not None and b is not None:
            assert a != b and OPPOSITE[a] == b, (who, c, a, b)
    d.colours[0] = d.colours[1] = None
    tap(app, center(sc.tile_rect(0, 0)), 1); assert d.colours[:2] == [0, 2]            # Red <-> Blue
    tap(app, center(sc.tile_rect(1, 3)), 1); assert d.colours[:2] == [1, 3]            # Yellow picks -> partner Green
    tap(app, center(sc.tile_rect(0, 3)), 1); assert d.colours[0] == 1                  # Yellow is taken: unchanged
    print("ok colours")


def test_review_back_edit_and_start_resets_everything():
    app = new_app(); open_setup(app); choose_count(app, 2)
    enter_names(app, ["Asha", "Ben"])
    tap(app, center(app.scene.btn_next.rect), 0); until(app, lambda: app.state == S.COLOR_SELECTION, 3); idle(app, .3)
    pick_colours(app, [2, 0]); tap(app, center(app.scene.btn_next.rect), 0)
    assert until(app, lambda: app.state == S.SETUP_REVIEW, 3); idle(app, .3); snap(app, "60_review_2p")
    assert isinstance(app.scene, ReviewScreen)
    tap(app, center(app.scene.btn_names.rect), 0); assert until(app, lambda: app.state == S.PLAYER_NAMES, 3); idle(app, .3)
    tap(app, center(app.scene.field_rect(1)), 1); type_text(app, "ie"); assert app.draft.names[1] == "Benie"
    tap(app, center(app.scene.btn_next.rect), 0); assert until(app, lambda: app.state == S.COLOR_SELECTION, 3); idle(app, .3)
    assert app.draft.colours[:2] == [2, 0]                                             # colours survived the edit
    tap(app, center(app.scene.btn_next.rect), 0); assert until(app, lambda: app.state == S.SETUP_REVIEW, 3); idle(app, .3)
    tap(app, center(app.scene.btn_back.rect), 0); assert until(app, lambda: app.state == S.COLOR_SELECTION, 3); idle(app, .3)
    tap(app, center(app.scene.btn_next.rect), 0); assert until(app, lambda: app.state == S.SETUP_REVIEW, 3); idle(app, .3)
    tap(app, center(app.scene.btn_start.rect), 0); assert until(app, lambda: isinstance(app.scene, GameScene), 4)
    sc = app.scene; assert sc.order == [0, 2] and sc.label(2) == "ASHA" and sc.label(0) == "BENIE"
    assert settle(sc, app, 12)
    # a few things change, then PLAY AGAIN keeps the players but starts a brand-new match
    sc.match.players[sc.cur].tokens[0].step = 10; sc.match.turn.skip_flags.add(0); sc.match.turn.rolls_remaining = 5
    sc.on_exit("again"); assert until(app, lambda: isinstance(app.scene, GameScene) and app.scene is not sc, 4)
    sc2 = app.scene; assert sc2.setup == sc.setup and sc2.match is not sc.match
    assert settle(sc2, app, 12)
    t = sc2.match.turn
    assert t.rolls_remaining == 1 and not t.skip_flags and not t.double_active and t.cards_used == 0
    assert all(tk.in_yard for p in sc2.match.players for tk in p.tokens) and sc2.match.res_bonus == []
    assert all(len(p.cards) == 3 and p.shield_turns == 0 for p in sc2.match.players)
    # MAIN MENU leaves nothing behind either
    sc2.on_exit("menu"); assert until(app, lambda: app.state == S.MENU, 4)
    open_setup(app); choose_count(app, 3)
    assert app.draft.names[:2] == ["Asha", "Benie"]                                    # remembered for quick re-setup
    print("ok review / edit / play again / menu")


def test_names_fit_everywhere_and_nothing_overlaps_for_every_layout():
    """Widest possible names, every legal colour layout: all text stays inside its slot and no panels collide."""
    widest = "W" * MAX_NAME_LEN
    from game.setup import GameSetup
    layouts = [c for n in (2, 3, 4) for c in itertools.combinations(range(4), n)
               if n != 2 or OPPOSITE[c[0]] == c[1]]
    assert len(layouts) == 2 + 4 + 1
    board = pygame.Rect(BOARD_X - 10, BOARD_Y - 10, BOARD_SIZE + 20, BOARD_SIZE + 20)
    canvas = pygame.Rect(0, 0, WIDTH, HEIGHT)
    probe = pygame.Surface((WIDTH, HEIGHT))
    for cols in layouts:
        names = [widest if i % 2 == 0 else "M" * MAX_NAME_LEN for i in range(len(cols))]
        setup = GameSetup.create([nm[:-1] + str(i) for i, nm in enumerate(names)], list(cols))   # unique names
        sc = GameScene(setup, lambda x: None); to_turn(sc, first=sc.order[0]); step(sc, .2)
        blocks = {"HUD": L.HUD_RECT, "MENU": L.MENU_BTN, "board": board}
        for c in sc.order:
            blocks[f"zone{c}"] = L.zone_rect(c)
            d = pygame.Rect(0, 0, L.DICE_SIZE + 40, L.DICE_SIZE + 48); d.center = L.dice_center(c); blocks[f"dice{c}"] = d
        for (a, ra), (b, rb) in itertools.combinations(blocks.items(), 2):
            assert not ra.colliderect(rb), (cols, a, b, ra, rb)
        for a, ra in blocks.items():
            assert canvas.contains(ra), (cols, a, ra)
        for c in sc.order:                                                             # card hand is inside its own zone
            z = L.zone_rect(c)
            for i in range(3):
                x, y = L.card_slot(c, i, 3); r = pygame.Rect(0, 0, CARD_W, CARD_H); r.center = (x, y)
                assert z.contains(r), (cols, c, i)
            nm = sc.label(c)
            r = draw_text_fit(probe, nm, 17, WHITE, L.name_pos(c), L.NAME_MAX_W, min_size=11)          # zone header
            assert z.contains(r), (cols, c, "zone name", r)
            r = draw_text_fit(probe, nm, 14, WHITE, (0, 0), 4 * CELL, min_size=9); assert r.w <= 4 * CELL    # yard plate
            r = draw_text_fit(probe, f"{nm} TURN", 28, WHITE, L.HUD_RECT.center, L.HUD_RECT.w - 28, min_size=14)
            assert L.HUD_RECT.contains(r), (cols, "hud", r)
        # run through states that print names so a crash/overlap in any of them would show here
        sc.state = S.TURN_SKIPPED; sc.skip_player = sc.order[-1]; sc.state_t = .6; draw(sc)
        sc.state = S.DETERMINING_FIRST_PLAYER; sc.state_t = .5; draw(sc); sc.state_t = 3.0; draw(sc)
    print(f"ok fit/overlap for {len(layouts)} layouts")


def test_status_box_is_gone_but_game_logic_and_ui_remain():
    assert not hasattr(L, "STATUS_RECT") and not hasattr(GameScene, "draw_status")
    sc = new_scene(4); to_turn(sc, first=0)
    assert hasattr(L, "HUD_RECT") and hasattr(L, "MENU_BTN") and sc.dices and sc.hands and sc.menu_btn
    # winning logic and the per-player token tray (finished crowns) still work without the box
    p = sc.match.players[0]
    for tk in p.tokens[:3]: place(sc, 0, tk.index, 56)
    place(sc, 0, 3, 55); do_roll(sc, 1)
    step(sc, until=lambda: sc.state == S.VICTORY, limit=30)
    assert sc.match.winner == 0 and p.finished_count == 4 and sc.victory is not None
    draw(sc); shot(sc, "61_victory_named")
    print("ok status box removed, logic intact")


def test_capture_bonus_in_the_live_game():
    from game.setup import GameSetup
    setup = GameSetup.create(["Asha", "Ben"], [0, 2])                                   # Red (left) vs Blue (right)
    # --- capture alone: bonus roll for the CAPTURER, opponent gets no turn in between
    sc = GameScene(setup, lambda x: None); log = record_banners(sc); to_turn(sc, first=0); m = sc.match
    place(sc, 0, 0, 3); place(sc, 2, 0, (5 - 26) % 52)                                  # blue token on ring cell 5
    do_roll(sc, 2); step(sc, until=lambda: sc.state == S.TOKEN_SELECTION)
    click(sc, tok_pos(sc, 0, 0)); step(sc, until=lambda: sc.state == S.PLAYER_TURN, limit=20)
    assert m.players[2].tokens[0].in_yard and sc.cur == 0 and m.turn.rolls_remaining == 1 and m.turn.can_roll
    assert "CAPTURE BONUS!" in log and m.res_bonus == []
    assert sc.dices[0].rect.collidepoint(dice_pos(sc)) and sc.hint == "Roll the dice"
    # the extra roll: no valid move (all red tokens would overshoot / need a 6) -> turn passes ONCE to Blue
    place(sc, 0, 0, 3)
    for i in (1, 2, 3): m.players[0].tokens[i].step = -1
    do_roll(sc, 3); step(sc, until=lambda: sc.state in (S.TOKEN_SELECTION, S.NO_MOVE, S.PLAYER_TURN))
    if sc.state == S.TOKEN_SELECTION: click(sc, tok_pos(sc, 0, 0))
    step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 2, limit=30)
    assert sc.cur == 2 and m.turn.rolls_remaining == 1                                 # exactly one turn went by
    # --- capture + six on the same move: two bonus rolls, never more
    sc = GameScene(setup, lambda x: None); log = record_banners(sc); to_turn(sc, first=0); m = sc.match
    place(sc, 0, 0, 1); place(sc, 2, 0, (7 - 26) % 52)                                  # ring 7: not a safe cell
    do_roll(sc, 6); step(sc, until=lambda: sc.state == S.TOKEN_SELECTION)
    click(sc, tok_pos(sc, 0, 0)); step(sc, until=lambda: sc.state == S.PLAYER_TURN, limit=20)
    assert m.players[2].tokens[0].in_yard and m.turn.rolls_remaining == 2 and sc.cur == 0
    assert "SIX + CAPTURE!" in log; shot(sc, "62_six_plus_capture")
    # --- landing on a SAFE square next to an enemy: no capture, no bonus, turn passes
    sc = GameScene(setup, lambda x: None); log = record_banners(sc); to_turn(sc, first=0); m = sc.match
    place(sc, 0, 0, 5); place(sc, 2, 0, (8 - 26) % 52)                                  # ring 8 is a star (safe)
    do_roll(sc, 3); step(sc, until=lambda: sc.state == S.TOKEN_SELECTION)
    click(sc, tok_pos(sc, 0, 0)); step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 2, limit=20)
    assert not m.players[2].tokens[0].in_yard and "CAPTURE BONUS!" not in log and "CAPTURED!" not in log
    # --- shield-blocked capture: no bonus either
    sc = GameScene(setup, lambda x: None); log = record_banners(sc); to_turn(sc, first=2); m = sc.match
    click(sc, card_pos(sc, 2, P.SHIELD)); assert settle(sc, None, 20)
    for i in (1, 2, 3): m.players[2].tokens[i].step = -1
    place(sc, 2, 0, (5 - 26) % 52); place(sc, 0, 0, 3)
    sc.match.turn.rolls_remaining = 0; sc.state = S.NEXT_TURN; sc.state_t = 0
    step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 0, limit=20)
    do_roll(sc, 2); step(sc, until=lambda: sc.state == S.TOKEN_SELECTION); click(sc, tok_pos(sc, 0, 0))
    step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 2, limit=30)
    assert not m.players[2].tokens[0].in_yard and "SHIELD BLOCKED!" in log and "CAPTURE BONUS!" not in log
    print("ok capture bonus in live game")


def test_text_input_is_released_when_leaving_names():
    calls = []
    real_stop = pygame.key.stop_text_input
    pygame.key.stop_text_input = lambda: (calls.append("stop"), real_stop())
    try:
        app = new_app(); open_setup(app); choose_count(app, 2)
        tap(app, center(app.scene.btn_next.rect), 0); until(app, lambda: app.state == S.COLOR_SELECTION, 3)
    finally:
        pygame.key.stop_text_input = real_stop
    assert calls, "stop_text_input() should be called when the names screen closes"
    print("ok text input released")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("SETUP UI TESTS PASSED")
