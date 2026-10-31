"""Bombs: exactly four per game, triggered by how far the game has progressed (a hidden timer).

* Progress = how close the LEADER is to winning (0.0 .. 1.0). It only ever counts upwards (we keep the
  peak), so a captured leader cannot "un-fire" a bomb.
* The four trigger points are 20/40/60/80 % of that progress, each shifted by a random +/-4 % so players
  cannot predict them. They are at least 12 % apart and all below 84 %, so all four always fall before
  anybody can win.
* A bomb marks 3-5 random ring squares (never a safe/star/start square, never a home lane or yard).
  When it explodes, every token standing on a marked square goes back to its yard - unless its owner has
  an active Shield. A bomb never gives anyone a bonus roll.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field

from game.board import RING_LEN, SAFE_RING, ring_index, is_on_ring
from game.token import Token
from config.settings import HOME_STEPS

BOMBS_PER_GAME = 4
BASE_POINTS = (0.20, 0.40, 0.60, 0.80)
JITTER = 0.04
MIN_TARGETS, MAX_TARGETS = 3, 5
BOMBABLE_CELLS = tuple(i for i in range(RING_LEN) if i not in SAFE_RING)     # 44 of the 52 ring squares

_PER_TOKEN = HOME_STEPS + 1                                                   # a finished token counts 57/57


def token_progress(token: Token) -> int:
    return 0 if token.step < 0 else min(token.step, HOME_STEPS) + 1


def leader_progress(players) -> float:
    """Fraction (0..1) of the way to victory for the player who is furthest ahead."""
    return max((sum(token_progress(t) for t in p.tokens) for p in players), default=0) / (4 * _PER_TOKEN)


@dataclass
class BombResult:
    cells: list[int]                                    # ring indices that exploded
    hit: list[Token] = field(default_factory=list)      # tokens sent back to their yard
    saved: list[Token] = field(default_factory=list)    # tokens on a bombed square that a Shield protected


class BombScheduler:
    def __init__(self, rng: random.Random, count: int = BOMBS_PER_GAME):
        self.rng = rng
        base = BASE_POINTS[:count]
        self.points = [round(p + rng.uniform(-JITTER, JITTER), 4) for p in base]
        self.fired = 0
        self.peak = 0.0
        self.armed: list[int] | None = None             # squares marked by a bomb that has not exploded yet

    @property
    def total(self) -> int:
        return len(self.points)

    @property
    def remaining(self) -> int:
        return self.total - self.fired

    def due(self, players) -> bool:
        """True when the next bomb should be armed now (call at a turn boundary)."""
        self.peak = max(self.peak, leader_progress(players))
        return self.armed is None and self.fired < self.total and self.peak >= self.points[self.fired]

    def arm(self) -> list[int]:
        assert self.armed is None, "a bomb is already armed"
        k = self.rng.randint(MIN_TARGETS, MAX_TARGETS)
        self.armed = sorted(self.rng.sample(BOMBABLE_CELLS, k))
        return list(self.armed)

    def detonate(self, players) -> BombResult:
        assert self.armed is not None, "nothing is armed"
        cells = set(self.armed)
        res = BombResult(sorted(cells))
        for p in players:
            for t in p.tokens:
                if is_on_ring(t.step) and ring_index(t.owner, t.step) in cells:
                    if p.shielded:
                        res.saved.append(t)
                    else:
                        t.reset()
                        res.hit.append(t)
        self.armed = None
        self.fired += 1
        return res
