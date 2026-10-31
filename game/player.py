from __future__ import annotations
from config.settings import PLAYER_NAMES
from game.token import Token
from powers.power_card import PowerType


class Player:
    """One seat. Colour index == seat index (0 Red, 1 Green, 2 Blue, 3 Yellow)."""

    def __init__(self, index: int, name: str | None = None):
        self.index = index                      # == board colour id (0 Red, 1 Green, 2 Blue, 3 Yellow)
        self.name = name or PLAYER_NAMES[index]
        self.tokens = [Token(index, i) for i in range(4)]
        # every player owns an independent hand of the same three cards
        self.cards: list[PowerType] = [PowerType.SHIELD, PowerType.DOUBLE_DICE, PowerType.SKIP]
        self.shield_turns = 0

    @property
    def label(self) -> str:
        """Display form used by the HUD, banners and zones (all-caps like the rest of the UI)."""
        return self.name.upper()

    @property
    def shielded(self) -> bool:
        return self.shield_turns > 0

    @property
    def finished_count(self) -> int:
        return sum(t.finished for t in self.tokens)

    @property
    def has_won(self) -> bool:
        return self.finished_count == 4

    def has_card(self, kind: PowerType) -> bool:
        return kind in self.cards

    def remove_card(self, kind: PowerType) -> None:
        self.cards.remove(kind)
