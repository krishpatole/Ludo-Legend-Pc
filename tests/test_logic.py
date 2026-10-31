"""Headless logic tests (no pygame needed). Run: python -m pytest tests  OR  python tests/test_logic.py"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.game import Match
from game.board import ring_index, RING, grid_pos, START_OFFSET
from game.rules import valid_tokens, apply_move
from powers import PowerType


def play_roll(m, value, pick=0):
    """Force a roll, auto-play first valid token. Returns (moved, bonus)."""
    m.dice.force(value)
    m.roll()
    v = m.valid_tokens()
    if not v:
        m.no_move(); return False, False
    m.move(v[min(pick, len(v) - 1)])
    return True, m.res_bonus


def test_yard_needs_six():
    m = Match(2, seed=1); m.start(0)
    m.dice.force(5); m.roll()
    assert m.valid_tokens() == []
    m.no_move(); assert not m.turn.can_roll


def test_six_bonus_and_exit():
    m = Match(2, seed=1); m.start(0)
    moved, bonus = play_roll(m, 6)
    assert moved and bonus and m.turn.can_roll
    assert m.players[0].tokens[0].step == 0


def test_exact_finish():
    m = Match(2, seed=1); m.start(0)
    t = m.players[0].tokens[0]; t.step = 53
    assert [x for x in valid_tokens(m.players[0], 4)] == []   # 57 overshoots
    assert t in valid_tokens(m.players[0], 3)


def test_capture_and_safe():
    m = Match(2, seed=1); m.start(0)                 # Red (colour 0) vs Blue (colour 2)
    a, b = m.players[0].tokens[0], m.players[2].tokens[0]
    # red at step 3 (ring 3); blue sits on ring 5 -> blue step = (5 - 26) % 52
    a.step = 3; b.step = (5 - START_OFFSET[2]) % 52
    m.dice.force(2); m.roll(); r = m.move(a)
    assert b in r.captured and b.in_yard
    # safe cell (ring 8 is a star): no capture
    a.step = 6; b.step = (8 - START_OFFSET[2]) % 52
    m.turn.rolls_remaining = 1; m.dice.force(2); m.roll(); r = m.move(a)
    assert not r.captured and not b.in_yard


def test_shield_blocks_and_expires():
    m = Match(2, seed=1); m.start(2)          # Blue's turn: use shield
    assert m.can_use_card(2, PowerType.SHIELD)
    assert not m.can_use_card(0, PowerType.SHIELD)           # not their turn
    lines = m.use_card(2, PowerType.SHIELD)
    assert lines[0] == "SHIELD" and m.players[2].shield_turns == 2
    assert not m.can_use_card(2, PowerType.SKIP)              # one card per turn
    m.dice.force(3); m.roll(); m.no_move(); m.end_turn()      # activation turn is not counted
    assert m.players[2].shield_turns == 2
    # red attacks shielded blue token
    a, b = m.players[0].tokens[0], m.players[2].tokens[0]
    a.step = 3; b.step = (5 - START_OFFSET[2]) % 52
    m.dice.force(2); m.roll(); r = m.move(a)
    assert b in r.blocked and not r.captured and not b.in_yard
    assert m.res_bonus == []                                  # a blocked capture is NOT a capture: no bonus
    m.turn.rolls_remaining = 0; m.end_turn()                  # -> blue's turn
    m.dice.force(1); m.roll(); m.no_move(); m.end_turn()
    assert m.players[2].shield_turns == 1
    m.dice.force(1); m.roll(); m.no_move(); m.end_turn()      # red
    m.dice.force(1); m.roll(); m.no_move(); m.end_turn()      # blue
    assert m.players[2].shield_turns == 0


def test_card_locked_after_roll():
    m = Match(2, seed=1); m.start(0)
    m.dice.force(2); m.roll()
    assert not any(m.can_use_card(0, k) for k in PowerType)
    try: m.use_card(0, PowerType.SKIP); assert False
    except ValueError: pass


def test_skip():
    m = Match(3, seed=1); m.start(0)
    m.use_card(0, PowerType.SKIP)
    m.dice.force(1); m.roll(); m.no_move()
    info = m.end_turn()
    assert info.skipped == [1] and info.next_player == 2
    m.dice.force(1); m.roll(); m.no_move(); info = m.end_turn()
    assert info.next_player == 0 and not info.skipped          # skip consumed
    assert not m.players[0].has_card(PowerType.SKIP) and m.players[1].has_card(PowerType.SKIP)


def test_skip_two_players_replays():
    m = Match(2, seed=1); m.start(0); m.use_card(0, PowerType.SKIP)
    m.dice.force(1); m.roll(); m.no_move()
    info = m.end_turn(); assert info.skipped == [2] and info.next_player == 0


def test_double_dice_max_three_rolls():
    for seq in [(6, 6, 6, 6, 6), (6, 6, 1), (2, 6, 6), (3, 3, 3)]:
        m = Match(2, seed=1); m.start(0)
        for t in m.players[0].tokens[:3]: t.step = 20          # keep tokens movable
        m.use_card(0, PowerType.DOUBLE_DICE)
        n = 0
        while m.can_roll:
            play_roll(m, seq[n]); n += 1
        assert n <= 3, (seq, n)
        if seq[0] == 6 and seq[1] == 6: assert n == 3
        if seq == (3, 3, 3): assert n == 2
        if seq == (2, 6, 6): assert n == 3


def test_normal_six_chain_unbounded_but_single_otherwise():
    m = Match(2, seed=1); m.start(0)
    for t in m.players[0].tokens: t.step = 10
    n = 0
    for v in (6, 6, 6, 4):
        assert m.can_roll; play_roll(m, v); n += 1
    assert n == 4 and not m.can_roll


def test_win_ends_game():
    m = Match(2, seed=1); m.start(0)
    p = m.players[0]
    for t in p.tokens[:3]: t.step = 56
    p.tokens[3].step = 55
    play_roll(m, 1)
    assert m.winner == 0 and not m.can_roll


def test_geometry():
    for c in range(4):
        pts = [grid_pos(c, s) for s in range(-1, 57)]
        assert all(0 <= x <= 15 and 0 <= y <= 15 for x, y in pts)
    assert RING[ring_index(0, 0)] == (1, 6) and RING[ring_index(1, 0)] == (8, 1)
    assert RING[ring_index(2, 0)] == (13, 8) and RING[ring_index(3, 0)] == (6, 13)
    for c in range(4):                       # last ring step sits right before the lane
        assert RING[ring_index(c, 50)] in [(0, 7), (7, 0), (14, 7), (7, 14)]


def test_random_full_games_terminate():
    for n in (2, 3, 4):
        for seed in range(6):
            m = Match(n, seed=seed); m.start(m.pick_first_player()); rng = random.Random(seed)
            for _ in range(20000):
                if m.winner is not None: break
                p = m.current
                if m.turn.rolls_taken == 0 and rng.random() < .3:
                    k = rng.choice(list(PowerType))
                    if m.can_use_card(p.index, k): m.use_card(p.index, k)
                while m.can_roll and m.winner is None:
                    m.roll(); v = m.valid_tokens()
                    if v: m.move(rng.choice(v))
                    else: m.no_move()
                    assert m.turn.rolls_taken <= 3 or not m.turn.double_active
                if m.winner is None: m.end_turn()
            assert m.winner is not None, (n, seed)


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try: fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
