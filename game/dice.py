from __future__ import annotations
import random
from collections import deque


class Dice:
    """RNG wrapper. ``force`` lets tests script exact rolls."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._forced: deque[int] = deque()

    def force(self, *values: int) -> None:
        self._forced.extend(values)

    def roll(self) -> int:
        return self._forced.popleft() if self._forced else self._rng.randint(1, 6)
