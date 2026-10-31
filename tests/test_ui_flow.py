"""End-to-end UI flow tests: real GameScene, synthetic mouse clicks, scripted dice. Headless."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_harness import *
from game.board import token_px, ring_index
from powers.power_card import PowerType as P


def place(sc, seat, idx, step):
    tk = sc.match.players[seat].tokens[idx]; tk.step = step
    v = sc.views[(seat, idx)]; v.x, v.y = token_px(seat, step, idx); v.cell_key = v.logic_key()


def tok_pos(sc, seat, idx):
    v = sc.views[(seat, idx)]; return (int(v.pos[0]), int(v.pos[1]))


def settle_turn(sc, seat=None):
    step(sc, until=lambda: sc.state == S.PLAYER_TURN and (seat is None or sc.cur == seat), limit=40)


def test_card_rules_and_locking():
    sc = new_scene(4); to_turn(sc, first=0); m = sc.match
    # another player's card: refused
    click(sc, card_pos(sc, 2, P.SKIP)); assert sc.state == S.PLAYER_TURN and m.players[2].has_card(P.SKIP)
    # own card works, and rapid repeat clicks cannot double-activate or consume extra cards
    p = card_pos(sc, 0, P.SHIELD); click(sc, p); click(sc, p); click(sc, p)
    assert sc.state == S.POWER_ANIMATION and m.players[0].shield_turns == 2 and len(m.players[0].cards) == 2
    click(sc, card_pos(sc, 0, P.SKIP)); assert m.players[0].has_card(P.SKIP)       # clicked mid-animation
    click(sc, dice_pos(sc, 1)); assert m.turn.rolls_taken == 0       # another player's die is dead
    click(sc, dice_pos(sc)); assert sc.state == S.POWER_ANIMATION                 # dice disabled during card anim
    settle_turn(sc, 0)
    assert len(sc.hands[0]) == 2 and m.players[1].has_card(P.SHIELD)               # others' cards untouched
    # after rolling, cards lock
    do_roll(sc, 2); assert sc.state == S.DICE_ROLLING
    click(sc, card_pos(sc, 0, P.SKIP)); assert m.players[0].has_card(P.SKIP)
    click(sc, dice_pos(sc)); assert m.turn.rolls_taken == 1                       # no double roll while rolling
    step(sc, until=lambda: sc.state in (S.NO_MOVE,)); step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 1)
    print("ok card rules")


def test_capture_and_shield_block():
    sc = new_scene(4); to_turn(sc, first=0); m = sc.match
    place(sc, 0, 0, 3); place(sc, 1, 0, (5 - 13) % 52)       # red -> lands on green's cell
    do_roll(sc, 2); step(sc, until=lambda: sc.state == S.TOKEN_SELECTION)
    click(sc, tok_pos(sc, 0, 0))
    step(sc, until=lambda: sc.state == S.CAPTURE_ANIMATION); step(sc, .2); shot(sc, "20_capture")
    assert m.players[1].tokens[0].in_yard
    settle_turn(sc)
    assert sc.views[(1, 0)].cell_key == ("yard", 1, 0) and abs(sc.views[(1, 0)].x - token_px(1, -1, 0)[0]) < 1
    # --- shield block: green shields on its turn, red attacks later
    sc = new_scene(4); to_turn(sc, first=1); m = sc.match
    click(sc, card_pos(sc, 1, P.SHIELD)); settle_turn(sc, 1)
    place(sc, 0, 0, 3); place(sc, 1, 0, (5 - 13) % 52)
    do_roll(sc, 2); step(sc, until=lambda: sc.state == S.NO_MOVE or sc.state == S.NEXT_TURN)   # green: rolls 2 -> moves token
    if sc.state == S.TOKEN_SELECTION: click(sc, tok_pos(sc, 1, 0))
    step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 2, limit=60)               # -> blue (green moved on)
    # blue passes (no valid move), then red attacks the shielded green token
    place(sc, 1, 0, (5 - 13) % 52)
    m.dice.force(1); click(sc, dice_pos(sc)); step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 3, limit=60)
    m.dice.force(1); click(sc, dice_pos(sc)); step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 0, limit=60)
    shot(sc, "21_shield_before_attack")
    do_roll(sc, 2); step(sc, until=lambda: sc.state == S.TOKEN_SELECTION); click(sc, tok_pos(sc, 0, 0))
    step(sc, until=lambda: sc.state == S.CAPTURE_ANIMATION); step(sc, .25); shot(sc, "22_shield_block")
    assert not m.players[1].tokens[0].in_yard and m.players[1].shielded
    print("ok capture + shield block")


def test_skip():
    sc = new_scene(3); to_turn(sc, first=0); m = sc.match
    click(sc, card_pos(sc, 0, P.SKIP)); step(sc, 1.0); shot(sc, "23_skip_card"); settle_turn(sc, 0)
    do_roll(sc, 3); step(sc, until=lambda: sc.state == S.TURN_SKIPPED, limit=20)
    step(sc, .4); shot(sc, "24_turn_skipped"); assert sc.skip_player == 1
    settle_turn(sc); assert sc.cur == 2
    print("ok skip")


def test_double_dice_max_three():
    sc = new_scene(2); to_turn(sc, first=0); m = sc.match
    click(sc, card_pos(sc, 0, P.DOUBLE_DICE)); step(sc, 1.2); shot(sc, "25_double_card"); settle_turn(sc, 0)
    assert m.turn.rolls_remaining == 2 and m.turn.double_active
    shot(sc, "26_double_active")
    rolls = 0
    for _ in range(5):
        if sc.state != S.PLAYER_TURN or sc.cur != 0: break
        do_roll(sc, 6); rolls += 1
        step(sc, until=lambda: sc.state in (S.PLAYER_TURN, S.TOKEN_SELECTION, S.NEXT_TURN), limit=20)
        if sc.state == S.TOKEN_SELECTION: click(sc, tok_pos(sc, 0, sc.selectable[0].index))
        step(sc, until=lambda: sc.state in (S.PLAYER_TURN, S.NEXT_TURN), limit=20)
        if sc.state == S.NEXT_TURN: break
    assert rolls == 3, rolls
    print("ok double dice (3 rolls max)")


def test_victory_and_exit_buttons():
    exits = []
    sc = new_scene(2, exits); to_turn(sc, first=0); m = sc.match
    for i in range(3): place(sc, 0, i, 56)
    place(sc, 0, 3, 55)
    do_roll(sc, 1); step(sc, until=lambda: sc.state == S.TOKEN_SELECTION or sc.state == S.TOKEN_MOVEMENT)
    step(sc, until=lambda: sc.state == S.VICTORY, limit=30); step(sc, 1.8); shot(sc, "27_victory")
    assert m.winner == 0
    ov = sc.victory
    click(sc, ov.btn_again.rect.center); assert exits == ["again"], exits
    click(sc, ov.btn_menu.rect.center); assert exits == ["again", "menu"], exits
    print("ok victory")


def test_no_valid_move_and_animations_off():
    from config.settings import SETTINGS
    SETTINGS.animations = False
    try:
        sc = new_scene(4); to_turn(sc, first=0); m = sc.match
        do_roll(sc, 3); step(sc, until=lambda: sc.state == S.NO_MOVE, limit=5)
        step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 1, limit=10)
    finally:
        SETTINGS.animations = True
    print("ok no-move / animations off")


def test_all_player_counts_render():
    for n in (2, 3, 4):
        sc = new_scene(n); to_turn(sc, first=sc.order[-1]); step(sc, .3); shot(sc, f"30_players_{n}")
    print("ok 2/3/4 player boards")


def test_separate_dice_per_player():
    sc = new_scene(4); to_turn(sc, first=2); m = sc.match
    assert len(sc.dices) == 4 and len({id(d) for d in sc.dices.values()}) == 4
    # clicking someone else's dice does nothing
    click(sc, sc.dices[0].center); assert sc.state == S.PLAYER_TURN and m.turn.rolls_taken == 0
    # clicking the current player's own dice rolls ONLY that dice
    m.dice.force(4); click(sc, sc.dices[2].center); assert sc.state == S.DICE_ROLLING
    assert sc.dices[2].rolling and not any(d.rolling for i, d in sc.dices.items() if i != 2)
    step(sc, until=lambda: sc.state != S.DICE_ROLLING)
    assert sc.dices[2].value == 4 and all(sc.dices[i].value == 0 for i in (0, 1, 3))
    shot(sc, "50_separate_dice")
    # dice never overlap any zone / HUD / board
    from ui import layout as LL
    board = pygame.Rect(BOARD_X - 10, BOARD_Y - 10, BOARD_SIZE + 20, BOARD_SIZE + 20)
    blocks = [LL.zone_rect(i) for i in range(4)] + [LL.HUD_RECT, LL.MENU_BTN, board]
    for i in range(4):
        r = pygame.Rect(0, 0, LL.DICE_SIZE + 40, LL.DICE_SIZE + 48); r.center = LL.dice_center(i)
        assert pygame.Rect(0, 0, WIDTH, HEIGHT).contains(r), (i, r)
        assert not any(r.colliderect(b) for b in blocks), (i, r)
    print("ok separate dice")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"): fn()
    print("ALL UI FLOW TESTS PASSED")
