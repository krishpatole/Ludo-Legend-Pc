"""Soak test: a bot plays COMPLETE games through the real App loop using only synthetic clicks/typing on
real on-screen positions:  menu -> count -> names -> colours -> review -> game -> win -> PLAY AGAIN -> MAIN MENU.

It also checks the capture-bonus rule on EVERY move of every game, plus the usual invariants.
usage: test_soak.py [players 2|3|4] [seed] [animations 0|1]     (no args: all counts, 2 seeds)
"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_driver import *
from powers.power_card import PowerType as P
from game.setup import OPPOSITE
from game.board import ring_index, is_on_ring, SAFE_RING

NAMES = ["Asha", "Ben Carter", "Maximilian XIV", "Zoe", "WWWWWWWWWWWWWW", "Wolfgang Amadeus", "Dev", "李雷"]


def random_lineup(rng, n):
    if n == 2:
        a, b = rng.choice([(0, 2), (1, 3)])
        cols = [a, b] if rng.random() < .5 else [b, a]
    else:
        cols = rng.sample(range(4), n)
    names = rng.sample(NAMES, n)
    return names, cols


def check_invariants(sc):
    m = sc.match
    for p in m.players:
        assert 0 <= p.shield_turns <= 2
        for t in p.tokens: assert -1 <= t.step <= 56
        assert len(p.cards) == len(set(p.cards))
    t = m.turn
    assert t.rolls_remaining >= 0
    if t.double_active: assert t.rolls_taken <= 3
    if any(not pl.has_card(P.SHIELD) for pl in m.players):      # a blocked capture may legitimately share a cell
        return
    seen = {}
    for p in m.players:
        for tk in p.tokens:
            if is_on_ring(tk.step):
                seen.setdefault(ring_index(p.index, tk.step), set()).add(p.index)
    for cell, owners in seen.items():
        assert len(owners) == 1 or cell in SAFE_RING, ("two colours on unsafe cell", cell, owners)


def check_move_result(sc, mover, roll, stats):
    """The capture bonus belongs to the capturer, once per capturing move; sixes still bonus; no loops."""
    m, res = sc.match, sc.last_res
    if m.winner is not None:
        assert m.turn.rolls_remaining == 0; return
    cap = bool(res.captured)
    t = m.turn
    expected = (1 if roll == 6 else 0) + (1 if cap else 0)
    if t.double_active:
        expected = min(expected, max(0, 3 - t.rolls_taken))
    # rolls_remaining counts what is left AFTER this move (before the move it was 0 unless Double Dice gave one)
    assert t.rolls_remaining >= expected, (roll, cap, t.rolls_remaining, expected)
    if cap:
        stats["captures"] += 1
        if t.rolls_remaining > 0:
            assert sc.state in (S.PLAYER_TURN,) and sc.cur == mover, ("capturer must roll again", sc.state, sc.cur, mover)
            stats["capture_bonuses"] += 1
    if t.rolls_remaining == 0:
        assert sc.state == S.NEXT_TURN, sc.state
    if t.rolls_remaining > 0 and not m.winner:
        assert sc.cur == mover                                   # nobody else is ever given the turn mid-bonus


def bot_turn(app, sc, rng, stats):
    m = sc.match
    if sc.state == S.PLAYER_TURN and m.turn.rolls_taken == 0 and m.turn.cards_used == 0 and rng.random() < .35:
        cur = m.players[sc.cur]
        if cur.cards:
            tap(app, card_pos(sc, sc.cur, rng.choice(cur.cards)), 1); stats["cards"] += 1
            return
    if sc.state == S.PLAYER_TURN and m.can_roll:
        tap(app, sc.dice.center, 1); stats["rolls"] += 1; return
    if sc.state == S.TOKEN_SELECTION and sc.selectable:
        tk = rng.choice(sc.selectable); mover = sc.cur; roll = m.last_roll
        tap(app, tok_pos(sc, tk.owner, tk.index), 1); stats["moves"] += 1
        assert until(app, lambda: sc.state in (S.PLAYER_TURN, S.NEXT_TURN, S.VICTORY), 40), sc.state
        if sc.state != S.VICTORY: check_move_result(sc, mover, roll, stats)
        return
    app.frame(DT)


def run(players=(2, 3, 4), seeds=(0, 1)):
    from config.settings import SETTINGS
    SETTINGS.bombs = True                       # real games include the 4 hidden-timer bombs
    for n in players:
        for seed in seeds:
            rng = random.Random(seed * 100 + n)
            names, cols = random_lineup(rng, n)
            app = new_app(); stats = dict(cards=0, rolls=0, moves=0, captures=0, capture_bonuses=0)
            sc = start_game_via_ui(app, n, names, cols)
            assert sc.n == n and sorted(sc.order) == sorted(cols)
            frames = 0
            while app.scene.state != S.VICTORY:
                sc = app.scene
                bot_turn(app, sc, rng, stats); frames += 1
                if frames % 25 == 0: check_invariants(sc)
                assert frames < 60 * 60 * 25, f"game too long / stuck: n={n} seed={seed} state={sc.state} stats={stats}"
            sc = app.scene; w = sc.match.winner
            assert w is not None and sc.match.players[w].finished_count == 4
            assert sc.match.bombs.fired == 4 and sc.match.bombs.armed is None, ("bombs", sc.match.bombs.fired)
            assert sc.label(w) == names[cols.index(w)].upper()
            idle(app, 1.8)
            tap(app, center(sc.victory.btn_again.rect), 0)                    # PLAY AGAIN: same players, new match
            assert until(app, lambda: isinstance(app.scene, GameScene) and app.scene is not sc, 4), "play again failed"
            assert app.scene.setup == sc.setup and app.scene.match.winner is None
            assert until(app, lambda: app.scene.state == S.PLAYER_TURN, 12)
            t = app.scene.match.turn; assert t.rolls_remaining == 1 and not t.skip_flags
            app.on_game_exit("menu"); assert until(app, lambda: app.state == S.MENU, 4)
            print(f"ok n={n} seed={seed} colours={cols}: winner {sc.label(w)}, {frames/60:.0f}s simulated, bombs {sc.match.bombs.fired}/4, {stats}")
    print("SOAK OK")


if __name__ == "__main__":
    from config.settings import SETTINGS
    if len(sys.argv) > 3: SETTINGS.animations = bool(int(sys.argv[3]))
    if len(sys.argv) > 2: run((int(sys.argv[1]),), (int(sys.argv[2]),))
    else: run()
