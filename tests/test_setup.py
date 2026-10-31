"""Setup model: counts, custom names, unique colours, 2-player opposite rule, roster/turn order. Pure logic."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import itertools
from game.board import RING, START_OFFSET, YARD_ORIGIN, LANES, HOME_DIR, ring_index
from game.game import Match
from game.setup import (OPPOSITE, GameSetup, SetupDraft, SetupError, clean_name, default_name, MAX_NAME_LEN,
                        validate, COLOUR_NAMES)


def test_opposite_pairs_come_from_the_real_board_geometry():
    # Verified from geometry, not assumed: opposite == start cells are point-mirrors through the centre,
    # the yards are diagonal and the home lanes point in opposite directions.
    assert OPPOSITE == (2, 3, 0, 1)
    for c in range(4):
        o = OPPOSITE[c]
        (xa, ya), (xb, yb) = RING[START_OFFSET[c]], RING[START_OFFSET[o]]
        assert (14 - xa, 14 - ya) == (xb, yb), (c, o)
        assert (START_OFFSET[o] - START_OFFSET[c]) % 52 == 26
        assert (YARD_ORIGIN[c][0] != YARD_ORIGIN[o][0]) and (YARD_ORIGIN[c][1] != YARD_ORIGIN[o][1])
        assert HOME_DIR[c] == (-HOME_DIR[o][0], -HOME_DIR[o][1])
    # ...and the pairs the task suggested ("Red-Yellow", "Green-Blue") are NOT opposite on this board
    assert OPPOSITE[0] != 3 and OPPOSITE[1] != 2


def test_every_colour_has_correct_start_lane_and_safe_squares():
    from game.board import SAFE_RING, is_safe_step
    names = COLOUR_NAMES
    for c in range(4):
        assert ring_index(c, 0) == START_OFFSET[c] and ring_index(c, 0) in SAFE_RING   # start square is safe
        assert is_safe_step(c, 0) and is_safe_step(c, 8)                               # star 8 cells later
        assert len(LANES[c]) == 5, names[c]
        lane_cells = set(LANES[c]); ring = set(RING)
        assert not (lane_cells & ring)                                                 # lane is private
    assert len({tuple(LANES[c]) for c in range(4)}) == 4


def test_defaults():
    for n, cols in ((2, (0, 2)), (3, (0, 1, 2)), (4, (0, 1, 2, 3))):
        g = GameSetup.default(n)
        assert g.n == n and g.colours == cols and [p.name for p in g.players] == [default_name(i) for i in range(n)]


def test_name_cleaning():
    assert clean_name("", 0) == "Player 1" and clean_name("   ", 2) == "Player 3" and clean_name(None, 1) == "Player 2"
    assert clean_name("  Krish   Patole ", 0) == "Krish Patole"
    assert clean_name("A\x00B\tC\n", 0) == "AB C"
    long = "X" * 80
    assert len(clean_name(long, 0)) == MAX_NAME_LEN
    assert clean_name("Zoë ñ 名前", 0) == "Zoë ñ 名前"


def test_validation_rules():
    assert validate(["a", "b"], [0, 2]) == [] and validate(["a", "b"], [1, 3]) == []
    assert validate(["a", "b"], [0, 1])                     # adjacent: not allowed for 2 players
    assert validate(["a", "b"], [0, 3]) and validate(["a", "b"], [1, 2])      # Red-Yellow / Green-Blue rejected
    assert validate(["a", "b"], [2, 2])                     # same colour
    assert validate(["a", "b", "c"], [0, 1, 1])
    assert validate(["a", "b", "c"], [0, 1, 3]) == []       # any 3 distinct colours
    assert validate(["a", "A"], [0, 2])                     # duplicate names (case-insensitive)
    assert validate(["a", "b"], [0, None])
    assert validate(["a"], [0])                             # too few players
    try:
        GameSetup.create(["a", "b"], [0, 0]); assert False
    except SetupError:
        pass


def test_draft_unique_colours_disabled_and_toggle():
    d = SetupDraft(); d.set_count(4)
    assert d.pick_colour(0, 1) and d.colours[0] == 1
    assert d.block_reason(1, 1) is not None and not d.pick_colour(1, 1)       # taken -> disabled
    assert d.colours[1] is None
    assert d.block_reason(1, 2) is None and d.pick_colour(1, 2)
    assert d.pick_colour(0, 1) and d.colours[0] is None                       # click own colour again -> free it
    assert d.pick_colour(2, 1)                                                 # now someone else can take it
    d.auto_assign()
    assert d.colours_complete and sorted(d.colours[:4]) == [0, 1, 2, 3]
    gs = d.build(); assert gs.n == 4 and len(set(gs.colours)) == 4


def test_draft_two_players_always_opposite():
    d = SetupDraft(); d.set_count(2)
    for first in range(4):
        d.colours = [None] * 4
        assert d.pick_colour(0, first)
        assert d.colours[1] == OPPOSITE[first]                                 # partner is assigned the opposite corner
        assert d.block_reason(1, first) is not None                            # and cannot take the same colour
        assert d.build().colours == (first, OPPOSITE[first])
    d.colours = [None] * 4
    assert d.pick_colour(1, 3) and d.colours[0] == 1                           # player 2 may choose first too
    assert d.pick_colour(0, 0) and d.colours[1] == 2                           # re-picking re-couples
    for i in range(4):                                                         # never an invalid pair, whatever order
        for j in range(4):
            d.colours = [None] * 4; d.pick_colour(0, i); d.pick_colour(1, j)
            if d.colours_complete:
                assert validate(d.display_names(), d.colours[:2]) == [], (i, j, d.colours)


def test_draft_changing_count_resets_colours_but_keeps_names():
    d = SetupDraft(); d.set_count(3); d.set_name(0, "Ann"); d.pick_colour(0, 2)
    d.set_count(3); assert d.colours[0] == 2                                   # same count: kept
    d.set_count(2); assert d.colours[0] is None and d.names[0] == "Ann"
    assert d.display_names() == ["Ann", "Player 2"]


def test_duplicate_names_blocked():
    d = SetupDraft(); d.set_count(2); d.set_name(0, "Sam"); d.set_name(1, "sam")
    assert d.name_errors()
    d.set_name(1, "Sue"); assert not d.name_errors()
    d.set_name(0, "Player 2"); d.set_name(1, "")            # explicit name equals the other's default
    assert d.name_errors()


def test_roster_is_keyed_by_colour_and_ordered_clockwise():
    gs = GameSetup.create(["Zed", "Amy", "Bob"], [3, 0, 2])                    # P1=Yellow, P2=Red, P3=Blue
    m = Match(gs, seed=3)
    assert m.players.colours == [0, 2, 3] and m.turn.order == [0, 2, 3]
    assert m.players[0].name == "Amy" and m.players[2].name == "Bob" and m.players[3].name == "Zed"
    assert [p.name for p in m.players] == ["Amy", "Bob", "Zed"] and len(m.players) == 3
    assert 1 not in m.players
    try:
        m.players[1]; assert False
    except KeyError:
        pass
    assert all(t.owner == p.index for p in m.players for t in p.tokens)
    assert m.pick_first_player() in (0, 2, 3)
    m.start(2); assert m.current.name == "Bob"
    m.dice.force(1); m.roll(); m.no_move(); info = m.end_turn(); assert info.next_player == 3


def test_every_legal_colour_layout_plays_complete_games():
    import random
    from powers import PowerType
    layouts = [(0, 2), (1, 3)] + list(itertools.combinations(range(4), 3)) + [(0, 1, 2, 3)]
    for cols in layouts:
        for perm in {tuple(cols), tuple(reversed(cols))}:                      # who owns which colour varies
            names = [f"P{i}" for i in range(len(perm))]
            gs = GameSetup.create(names, list(perm))
            for seed in range(2):
                m = Match(gs, seed=seed); m.start(m.pick_first_player()); rng = random.Random(seed)
                for _ in range(30000):
                    if m.winner is not None: break
                    p = m.current
                    if m.turn.rolls_taken == 0 and rng.random() < .3:
                        k = rng.choice(list(PowerType))
                        if m.can_use_card(p.index, k): m.use_card(p.index, k)
                    while m.can_roll and m.winner is None:
                        m.roll(); v = m.valid_tokens()
                        if v: m.move(rng.choice(v))
                        else: m.no_move()
                    if m.winner is None: m.end_turn()
                assert m.winner in cols, (cols, seed)
                assert m.players[m.winner].finished_count == 4


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try: fn(); print("PASS", name)
            except Exception as e:
                import traceback; traceback.print_exc(); fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
