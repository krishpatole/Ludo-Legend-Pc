"""Turn order, roll budget (6-bonus / Double Dice cap), skip flags, shield countdown."""
from __future__ import annotations
from dataclasses import dataclass, field
from config.settings import MAX_DOUBLE_ROLLS


@dataclass
class TurnEnd:
    next_player: int
    skipped: list[int] = field(default_factory=list)


class TurnManager:
    def __init__(self, active: list[int]):
        self.order = list(active)            # clockwise seat order
        self.current = self.order[0]
        self.turn_number = 0
        self.skip_flags: set[int] = set()
        self._reset_turn_fields()

    def _reset_turn_fields(self) -> None:
        self.rolls_remaining = 1
        self.rolls_taken = 0
        self.double_active = False
        self.cards_used = 0
        self.shield_started_this_turn = False

    # ---- order -----------------------------------------------------------
    def next_after(self, player: int) -> int:
        return self.order[(self.order.index(player) + 1) % len(self.order)]

    def begin_turn(self, player: int) -> None:
        self.current = player
        self.turn_number += 1
        self._reset_turn_fields()

    # ---- rolls -----------------------------------------------------------
    @property
    def can_roll(self) -> bool:
        return self.rolls_remaining > 0

    def grant_double(self) -> None:
        """Double Dice: one extra roll. Only legal before the first roll."""
        assert self.rolls_taken == 0
        self.double_active = True
        self.rolls_remaining += 1

    def on_roll(self) -> None:
        assert self.rolls_remaining > 0
        self.rolls_taken += 1
        self.rolls_remaining -= 1

    def finish_roll(self, value: int, moved: bool, captured: bool = False) -> list[str]:
        """Called after a roll was resolved. Returns the bonus rolls that were actually granted
        (a list containing 'six' and/or 'capture').

        * a 6 that was actually played earns one bonus roll;
        * a legal capture earns one bonus roll for the capturing player (once per move);
        * both can apply to the same move and stack;
        * during a Double Dice turn the TOTAL number of rolls can never exceed MAX_DOUBLE_ROLLS (3),
          so bonuses beyond that are dropped.
        """
        granted: list[str] = []
        if value == 6 and moved:
            self.rolls_remaining += 1
            granted.append("six")
        if captured:
            self.rolls_remaining += 1
            granted.append("capture")
        if self.double_active:
            cap = max(0, MAX_DOUBLE_ROLLS - self.rolls_taken)
            dropped = max(0, self.rolls_remaining - cap)
            self.rolls_remaining -= dropped
            while dropped and granted:                   # the dropped rolls were the newest bonuses
                granted.pop()
                dropped -= 1
        return granted

    # ---- skip ------------------------------------------------------------
    def mark_skip_next(self) -> int:
        target = self.next_after(self.current)
        if target != self.current:
            self.skip_flags.add(target)
        return target

    # ---- end of turn -----------------------------------------------------
    def end_turn(self, players) -> TurnEnd:
        cur = players[self.current]
        if cur.shield_turns > 0 and not self.shield_started_this_turn:
            cur.shield_turns -= 1                       # 2 -> 1 -> expired
        nxt, skipped = self.next_after(self.current), []
        while nxt in self.skip_flags:
            self.skip_flags.discard(nxt)
            skipped.append(nxt)
            nxt = self.next_after(nxt)
        return TurnEnd(nxt, skipped)
