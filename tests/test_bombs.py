"""Bombs: exactly four per game on a hidden game-progress timer; 3-5 random non-safe ring squares;
tokens on those squares go home unless Shielded; never a bonus roll. Logic + live scene."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_driver import *            # dummy SDL, harness (bombs OFF by default), place/tok_pos/record_banners
from config.settings import SETTINGS
from game.game import Match
from game.bombs import (BombScheduler, BOMBABLE_CELLS, BOMBS_PER_GAME, MIN_TARGETS, MAX_TARGETS,
                        leader_progress, JITTER, BASE_POINTS)
from game.board import SAFE_RING, ring_index, RING_LEN
from powers.power_card import PowerType as P


def ring_step(colour, ring_idx):
    """The step at which `colour`'s token stands on ring square `ring_idx`."""
    from game.board import START_OFFSET
    return (ring_idx - START_OFFSET[colour]) % RING_LEN


# ----------------------------------------------------------------------------- pure logic
def test_exactly_four_bombs_in_every_simulated_game():
    for n in (2, 3, 4):
        for seed in range(25):
            m = Match(n, seed=seed); m.start(m.pick_first_player()); rng = random.Random(seed)
            for _ in range(40000):
                if m.winner is not None: break
                while m.can_roll and m.winner is None:
                    m.roll(); v = m.valid_tokens()
                    m.move(rng.choice(v)) if v else m.no_move()
                if m.winner is not None: break
                if m.bomb_due():
                    cells = m.arm_bomb(); m.detonate_bomb()
                m.end_turn()
            assert m.winner is not None
            assert m.bombs.fired == BOMBS_PER_GAME == 4, (n, seed, m.bombs.fired)
    print("ok exactly 4 bombs in 75 full games")


def test_hidden_timer_is_jittered_ordered_and_always_before_a_win():
    seen = set()
    for seed in range(200):
        pts = BombScheduler(random.Random(seed)).points
        assert len(pts) == 4 and pts == sorted(pts)
        assert all(abs(p - b) <= JITTER + 1e-9 for p, b in zip(pts, BASE_POINTS))
        assert all(b - a >= 0.12 - 1e-3 for a, b in zip(pts, pts[1:])), pts       # never bunched together
        assert pts[0] >= 0.16 - 1e-3 and pts[-1] <= 0.84 + 1e-3                      # all well before 100 %
        seen.add(tuple(pts))
    assert len(seen) > 150, "trigger points should differ from game to game (hidden)"
    print("ok hidden jittered timer")


def test_progress_measure_and_no_bomb_at_the_start():
    m = Match(4, seed=1); m.start(0)
    assert leader_progress(m.players) == 0 and not m.bomb_due()
    for t in m.players[0].tokens: t.step = 56
    assert leader_progress(m.players) == 1.0
    for t in m.players[0].tokens: t.reset()
    m.players[0].tokens[0].step = 50
    assert abs(leader_progress(m.players) - 51 / 228) < 1e-9
    print("ok progress")


def test_bomb_waits_until_the_leader_reaches_the_trigger_point():
    m = Match(2, seed=3); m.start(0)
    first = m.bombs.points[0]
    t = m.players[0].tokens
    t[0].step = 40; assert leader_progress(m.players) < first and not m.bomb_due()
    for tk in t: tk.step = 30                                    # 4 * 31/228 = 54 %
    assert m.bomb_due()
    m.arm_bomb()
    assert not m.bomb_due(), "no second bomb while one is armed"
    try: m.arm_bomb(); assert False
    except AssertionError: pass
    print("ok trigger point")


def test_peak_progress_means_a_captured_leader_cannot_cancel_a_bomb():
    m = Match(2, seed=5); m.start(0)
    for tk in m.players[0].tokens: tk.step = 30
    assert m.bomb_due()
    for tk in m.players[0].tokens: tk.reset()                      # leader gets wiped out
    assert m.bomb_due(), "the peak is remembered"
    print("ok peak")


def test_targets_are_3_to_5_distinct_and_never_safe_squares():
    seen_sizes = set()
    for seed in range(300):
        cells = BombScheduler(random.Random(seed)).arm()
        seen_sizes.add(len(cells))
        assert MIN_TARGETS <= len(cells) <= MAX_TARGETS and len(set(cells)) == len(cells)
        assert all(0 <= c < RING_LEN and c not in SAFE_RING for c in cells)
    assert seen_sizes == {3, 4, 5}
    assert len(BOMBABLE_CELLS) == RING_LEN - len(SAFE_RING) == 44
    print("ok targets")


def _armed_match(cells, n=4):
    m = Match(n, seed=9); m.start(0); m.bombs.armed = list(cells); return m


def test_only_unshielded_tokens_on_marked_squares_go_home():
    m = _armed_match([22, 36])
    a, b, c, d = m.players[1].tokens[0], m.players[2].tokens[0], m.players[3].tokens[0], m.players[0].tokens[0]
    a.step = ring_step(1, 22)                                      # on a marked square
    b.step = ring_step(2, 36)                                      # on a marked square
    c.step = ring_step(3, 44)                                      # ring square that is NOT marked
    d.step = 53                                                    # home lane: bombs never touch it
    e = m.players[1].tokens[1]; e.step = 56                        # finished
    res = m.detonate_bomb()
    assert sorted(map(id, res.hit)) == sorted([id(a), id(b)]) and a.in_yard and b.in_yard
    assert c.step == ring_step(3, 44) and d.step == 53 and e.step == 56 and not res.saved
    assert m.bombs.fired == 1 and m.bombs.armed is None
    print("ok detonation")


def test_shield_makes_tokens_immune_to_bombs():
    m = _armed_match([22, 36])
    a, b = m.players[1].tokens[0], m.players[2].tokens[0]
    a.step = ring_step(1, 22); b.step = ring_step(2, 36)
    m.players[1].shield_turns = 2
    res = m.detonate_bomb()
    assert [id(x) for x in res.saved] == [id(a)] and [id(x) for x in res.hit] == [id(b)] and a.step == ring_step(1, 22) and b.in_yard
    print("ok shield vs bomb")


def test_two_tokens_of_one_colour_on_one_marked_square_both_go_home():
    m = _armed_match([22])
    for tk in m.players[1].tokens[:2]: tk.step = ring_step(1, 22)
    res = m.detonate_bomb()
    assert len(res.hit) == 2 and all(t.in_yard for t in m.players[1].tokens[:2])
    print("ok stacked tokens")


def test_bomb_never_gives_a_bonus_roll_or_changes_whose_turn_it_is():
    m = _armed_match([22], n=3)
    m.players[1].tokens[0].step = ring_step(1, 22)
    cur, rolls, bonus = m.turn.current, m.turn.rolls_remaining, list(m.res_bonus)
    m.detonate_bomb()
    assert (m.turn.current, m.turn.rolls_remaining, m.res_bonus) == (cur, rolls, bonus)
    assert m.end_turn().next_player == 1 and m.turn.rolls_remaining == 1
    print("ok no bonus")


def test_no_bomb_once_the_game_is_won_and_fresh_matches_start_clean():
    m = Match(2, seed=2); m.start(0)
    for tk in m.players[0].tokens: tk.step = 56
    m.winner = 0
    assert not m.bomb_due()
    fresh = Match(2, seed=2)
    assert fresh.bombs.fired == 0 and fresh.bombs.armed is None and fresh.bombs.peak == 0
    print("ok win / restart")


def test_bombs_do_not_disturb_the_seeded_dice_sequence():
    a, b = Match(4, seed=11), Match(4, seed=11)
    for _ in range(5): b.bombs.arm(); b.bombs.armed = None          # burn bomb RNG
    assert a.pick_first_player() == b.pick_first_player()
    assert [a.dice.roll() for _ in range(20)] == [b.dice.roll() for _ in range(20)]
    print("ok rng independence")


# ----------------------------------------------------------------------------- live scene
def _scene_at_end_of_turn(n=4, forced=None, shield_seat=None, bombs=True):
    """Seat 0's four tokens wait on step 55 (leader at ~98 %), so any roll but 1 = no move = turn ends.
    Seat 1/2/3 each get one token on the ring (idx 22 / 36 / 44)."""
    SETTINGS.bombs = bombs
    sc = new_scene(n); to_turn(sc, first=0); m = sc.match
    for i in range(4): place(sc, 0, i, 55)
    place(sc, 1, 0, ring_step(1, 22)); place(sc, 2, 0, ring_step(2, 36))
    if n == 4: place(sc, 3, 0, ring_step(3, 44))
    if shield_seat is not None: m.players[shield_seat].shield_turns = 2
    cells = list(forced or [22, 36])
    def forced_arm():
        m.bombs.armed = list(cells); return list(cells)
    m.bombs.arm = forced_arm
    return sc, m, cells


def test_live_bomb_warning_explosion_and_tokens_fly_home():
    sc, m, cells = _scene_at_end_of_turn()
    log = record_banners(sc); states = []
    do_roll(sc, 3)
    assert step(sc, until=lambda: sc.state == S.BOMB_WARNING, limit=15), sc.state
    assert sc.bomb_cells == cells and m.bombs.fired == 0 and m.bombs.armed == cells
    assert "BOMB INCOMING!" in log
    step(sc, 1.6); shot(sc, "70_bomb_warning")
    assert sc.state == S.BOMB_WARNING and not m.players[1].tokens[0].in_yard      # nobody moves during the warning
    click(sc, dice_pos(sc)); click(sc, (int(sc.hands[0][0].x), int(sc.hands[0][0].y)))
    assert sc.state == S.BOMB_WARNING and m.turn.rolls_taken == 1                  # dice / cards ignored
    assert step(sc, until=lambda: sc.state == S.BOMB_EXPLOSION, limit=10)
    step(sc, .25); shot(sc, "71_bomb_blast")
    assert m.players[1].tokens[0].in_yard and m.players[2].tokens[0].in_yard
    assert m.players[3].tokens[0].step == ring_step(3, 44)                        # unmarked square: survives
    assert m.bombs.fired == 1 and any("2 TOKENS SENT HOME" in x for x in log)
    assert step(sc, until=lambda: sc.state == S.PLAYER_TURN, limit=15)
    assert sc.cur == 1 and m.turn.rolls_remaining == 1, "normal next player, no bonus roll"
    for c in (1, 2):
        v = sc.views[(c, 0)]
        assert v.cell_key == ("yard", c, 0) and abs(v.x - token_px_yard(c)[0]) < 1.5 and not v.moving
    draw(sc); shot(sc, "72_after_bomb")
    print("ok live bomb")


def token_px_yard(c, idx=0):
    from game.board import token_px, STEP_YARD
    return token_px(c, STEP_YARD, idx)


def test_live_shield_blocks_the_bomb():
    sc, m, cells = _scene_at_end_of_turn(shield_seat=1)
    log = record_banners(sc)
    do_roll(sc, 3)
    assert step(sc, until=lambda: sc.state == S.BOMB_EXPLOSION, limit=20)
    assert not m.players[1].tokens[0].in_yard and m.players[2].tokens[0].in_yard
    assert "SHIELD BLOCKED THE BOMB!" in log and any("1 TOKEN SENT HOME" in x for x in log)
    step(sc, .3); shot(sc, "73_bomb_shield")
    assert step(sc, until=lambda: sc.state == S.PLAYER_TURN, limit=15)
    print("ok live shield")


def test_live_nobody_hit_message_and_bombs_off_setting():
    sc, m, cells = _scene_at_end_of_turn(forced=[2, 4])               # empty squares
    log = record_banners(sc); do_roll(sc, 3)
    assert step(sc, until=lambda: sc.state == S.BOMB_EXPLOSION, limit=20)
    assert "BOMB! NOBODY WAS HIT" in log
    assert step(sc, until=lambda: sc.state == S.PLAYER_TURN, limit=15)
    # BOMBS option OFF: same position, but no bomb ever
    sc, m, cells = _scene_at_end_of_turn(bombs=False); seen = set()
    do_roll(sc, 3)
    assert step(sc, until=lambda: sc.state == S.PLAYER_TURN and sc.cur == 1, limit=15)
    assert m.bombs.fired == 0 and m.bombs.armed is None
    print("ok nobody hit / option off")


def test_live_bomb_with_animations_off_and_three_players():
    SETTINGS.animations = False
    try:
        sc, m, cells = _scene_at_end_of_turn(n=3)
        do_roll(sc, 3)
        assert step(sc, until=lambda: sc.state == S.BOMB_EXPLOSION, limit=10)
        assert step(sc, until=lambda: sc.state == S.PLAYER_TURN, limit=10) and m.bombs.fired == 1
    finally:
        SETTINGS.animations = True
    print("ok animations off / 3 players")


def test_hud_counter_and_options_toggle_exist():
    SETTINGS.bombs = True
    sc = new_scene(2); to_turn(sc, first=0); step(sc, .3); shot(sc, "74_hud_bombs")
    from ui.menu import OptionsScreen
    o = OptionsScreen(lambda: None, lambda: None)
    assert [t.attr for t in o.toggles] == ["music", "sfx", "animations", "bombs"]
    SETTINGS.bombs = False
    print("ok hud / options")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    SETTINGS.bombs = False
    print("ALL BOMB TESTS PASSED")
