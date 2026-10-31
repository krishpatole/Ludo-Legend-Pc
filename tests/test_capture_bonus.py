"""Capture bonus turn: the player who captures rolls again. Pure logic, no pygame."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.game import Match
from game.setup import GameSetup
from game.board import START_OFFSET, SAFE_RING, ring_index
from powers import PowerType as P


def step_on(colour, ring_cell):
    """Token step that puts `colour`'s token on global ring index `ring_cell`."""
    return (ring_cell - START_OFFSET[colour]) % 52


def roll_move(m, value, token=None):
    """Force a roll and play it (first valid token unless given). Returns the MoveResult or None."""
    m.dice.force(value); m.roll()
    v = m.valid_tokens()
    if not v:
        m.no_move(); return None
    return m.move(token if token in v else v[0])


def red_blue(seed=1):
    m = Match(2, seed=seed); m.start(0)               # Red (0) vs Blue (2)
    return m, m.players[0].tokens, m.players[2].tokens


def test_capture_gives_the_capturer_one_extra_roll():
    m, red, blue = red_blue()
    red[0].step = 3; blue[0].step = step_on(2, 5)
    r = roll_move(m, 2, red[0])
    assert r.captured == [blue[0]] and blue[0].in_yard
    assert m.res_bonus == ["capture"]
    assert m.turn.rolls_remaining == 1 and m.can_roll
    assert m.turn.current == 0                        # still Red's turn: Blue gets NOTHING in between
    # Red uses the bonus roll; only afterwards does the turn pass to Blue
    roll_move(m, 1, red[0])                           # plain move, no bonus
    assert not m.can_roll
    assert m.end_turn().next_player == 2


def test_bonus_goes_to_capturer_never_to_the_captured_player():
    m, red, blue = red_blue()
    m.turn.begin_turn(2)                               # Blue's turn this time
    blue[0].step = 3                                   # ring 29
    red[0].step = ring_index(2, 5)                     # a red token on ring 31 (red step 31), 2 ahead of blue's token
    assert ring_index(0, red[0].step) == ring_index(2, 5)
    r = roll_move(m, 2, blue[0])
    assert r.captured == [red[0]] and red[0].in_yard
    assert m.res_bonus == ["capture"]
    assert m.turn.current == 2 and m.turn.rolls_remaining == 1      # Blue (the capturer) rolls again, Red does not
    roll_move(m, 1, blue[0])
    assert m.end_turn().next_player == 0                            # only now does Red (the captured player) play


def test_no_bonus_on_safe_squares():
    for safe_ring in sorted(SAFE_RING):
        m, red, blue = red_blue()
        s_red = step_on(0, (safe_ring - 2) % 52)
        if s_red > 50: continue
        red[0].step = s_red; blue[0].step = step_on(2, safe_ring)
        if blue[0].step > 50: continue
        r = roll_move(m, 2, red[0])
        assert not r.captured and not blue[0].in_yard, safe_ring
        assert m.res_bonus == [] and m.turn.rolls_remaining == 0, safe_ring
    # landing on the opponent's own start square is safe too
    m, red, blue = red_blue()
    red[0].step = step_on(0, START_OFFSET[2] - 2); blue[0].step = 0
    r = roll_move(m, 2, red[0]); assert not r.captured and blue[0].step == 0 and m.res_bonus == []


def test_shield_blocked_capture_gives_no_bonus():
    m, red, blue = red_blue()
    m.players[2].shield_turns = 2
    red[0].step = 3; blue[0].step = step_on(2, 5)
    r = roll_move(m, 2, red[0])
    assert r.blocked == [blue[0]] and not r.captured
    assert m.res_bonus == [] and m.turn.rolls_remaining == 0


def test_capture_and_six_stack_without_extra_loop():
    m, red, blue = red_blue()
    red[0].step = 4; blue[0].step = step_on(2, 10)     # a 6 moves red 4 -> 10 and captures
    r = roll_move(m, 6, red[0])
    assert r.captured and m.res_bonus == ["six", "capture"]
    assert m.turn.rolls_remaining == 2 and m.turn.current == 0
    roll_move(m, 3); roll_move(m, 3)                   # two ordinary bonus rolls, then it ends (no infinite loop)
    assert not m.can_roll and m.end_turn().next_player == 2


def test_six_alone_unchanged_and_capture_alone_is_one_roll():
    m, red, blue = red_blue()
    red[0].step = 4
    roll_move(m, 6, red[0]); assert m.res_bonus == ["six"] and m.turn.rolls_remaining == 1
    m, red, blue = red_blue()
    roll_move(m, 6); assert m.turn.rolls_remaining == 1              # leaving the yard on a 6 still just one bonus
    red[0].step = 3; blue[0].step = step_on(2, 5)
    roll_move(m, 2, red[0]); assert m.res_bonus == ["capture"] and m.turn.rolls_remaining == 1


def test_multiple_captured_tokens_in_one_move_is_one_bonus():
    gs = GameSetup.create(["R", "B", "Y"], [0, 2, 3])
    m = Match(gs, seed=2); m.start(0)
    red = m.players[0].tokens[0]; blue = m.players[2].tokens[0]; yel = m.players[3].tokens[0]
    red.step = 3; blue.step = step_on(2, 5); yel.step = step_on(3, 5)
    r = roll_move(m, 2, red)
    assert len(r.captured) == 2 and blue in r.captured and yel in r.captured and blue.in_yard and yel.in_yard
    assert m.res_bonus == ["capture"] and m.turn.rolls_remaining == 1      # NOT two bonuses


def test_chained_captures_each_earn_a_bonus_and_never_skip_players():
    gs = GameSetup.create(["R", "B", "Y"], [0, 2, 3])
    m = Match(gs, seed=2); m.start(0)
    red = m.players[0].tokens
    red[0].step = 3; red[1].step = 20
    m.players[2].tokens[0].step = step_on(2, 5)
    m.players[3].tokens[0].step = step_on(3, 22)
    roll_move(m, 2, red[0]); assert m.res_bonus == ["capture"] and m.turn.current == 0
    roll_move(m, 2, red[1]); assert m.res_bonus == ["capture"] and m.turn.current == 0   # second capture, second bonus
    assert m.turn.rolls_remaining == 1
    roll_move(m, 1); assert not m.can_roll
    assert m.end_turn().next_player == 2                                                  # Blue, nobody skipped
    assert m.turn.current == 2


def test_double_dice_cap_of_three_rolls_holds_with_capture_bonuses():
    for first_six in (False, True):
        m, red, blue = red_blue()
        for t in red[1:]: t.step = 30
        red[0].step = 3
        m.use_card(0, P.DOUBLE_DICE)                                       # normal roll + one extra
        blue[0].step = step_on(2, 5)
        rolls = 0
        roll_move(m, 6 if first_six else 2, red[0]); rolls += 1            # roll 1 captures (+six?)
        assert m.turn.rolls_remaining <= 3 - m.turn.rolls_taken
        blue[1].step = step_on(2, 20); red[0].step = 18
        while m.can_roll:
            roll_move(m, 2, red[0]); rolls += 1
            assert m.turn.rolls_taken <= 3
        assert m.turn.rolls_taken == 3 and rolls == 3, (first_six, rolls)  # never a 4th roll


def test_capture_on_the_third_double_dice_roll_gives_nothing():
    m, red, blue = red_blue()
    red[2].step = red[3].step = 30
    red[0].step = 10; red[1].step = 3
    blue[0].step = step_on(2, 5)
    m.use_card(0, P.DOUBLE_DICE)                       # roll 1 + one extra roll
    roll_move(m, 2, red[0]); assert m.turn.rolls_taken == 1 and m.can_roll          # roll 1: plain move
    roll_move(m, 6, red[0]); assert m.res_bonus == ["six"] and m.can_roll           # roll 2 is a played six -> roll 3
    assert m.turn.rolls_taken == 2 and m.turn.rolls_remaining == 1
    r = roll_move(m, 2, red[1])                                                     # roll 3 captures
    assert r.captured and blue[0].in_yard and m.turn.rolls_taken == 3
    assert m.res_bonus == [] and not m.can_roll and m.turn.rolls_remaining == 0, "no 4th roll even after a capture"
    assert m.end_turn().next_player == 2


def test_skip_card_interaction_with_capture_bonus():
    gs = GameSetup.create(["R", "B", "Y"], [0, 2, 3]); m = Match(gs, seed=2); m.start(0)
    m.use_card(0, P.SKIP)                                                  # Blue (next) will be skipped
    red, blue = m.players[0].tokens[0], m.players[2].tokens[0]
    red.step = 3; blue.step = step_on(2, 5)
    roll_move(m, 2, red); assert m.turn.rolls_remaining == 1 and m.turn.skip_flags == {2}
    roll_move(m, 1)                                                        # bonus roll
    info = m.end_turn()
    assert info.skipped == [2] and info.next_player == 3 and m.turn.skip_flags == set()


def test_shield_interaction_with_capture_bonus():
    m, red, blue = red_blue()
    m.use_card(0, P.SHIELD)                                                # red shielded for 2 turns
    red[0].step = 3; blue[0].step = step_on(2, 5)
    roll_move(m, 2, red[0])                                                # shielded players can still capture
    assert blue[0].in_yard and m.turn.rolls_remaining == 1
    roll_move(m, 1)                                                        # bonus roll inside the SAME turn
    m.end_turn()
    assert m.players[0].shield_turns == 2                                  # activation turn not counted, no double decrement
    m.dice.force(1); m.roll(); m.no_move(); m.end_turn()                   # blue
    m.dice.force(1); m.roll(); m.no_move(); m.end_turn()                   # red's 1st counted turn ends
    assert m.players[0].shield_turns == 1


def test_win_clears_every_pending_roll():
    m, red, blue = red_blue()
    for t in red[:3]: t.step = 56
    red[3].step = 50; blue[0].step = step_on(2, 5)
    m.dice.force(6); m.roll()                                              # 50 + 6 = 56 -> home, would also earn a six bonus
    m.move(red[3])
    assert m.winner == 0 and m.turn.rolls_remaining == 0 and not m.can_roll and m.res_bonus == []


def test_fresh_match_has_no_leftover_bonus_state():
    m, red, blue = red_blue()
    red[0].step = 3; blue[0].step = step_on(2, 5)
    roll_move(m, 2, red[0]); assert m.turn.rolls_remaining == 1
    m2 = Match(2, seed=1); m2.start(0)                                     # "play again" / new game
    assert m2.turn.rolls_remaining == 1 and m2.res_bonus == [] and m2.winner is None and m2.turn.current == 0


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try: fn(); print("PASS", name)
            except Exception as e:
                import traceback; traceback.print_exc(); fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
