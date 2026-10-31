"""Power card definitions + the effect base class."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class PowerType(Enum):
    SHIELD = "shield"
    DOUBLE_DICE = "double_dice"
    SKIP = "skip"


@dataclass(frozen=True)
class CardInfo:
    name: str
    desc: tuple[str, ...]       # description lines shown on the card
    top: tuple[int, int, int]   # gradient colours
    bottom: tuple[int, int, int]
    accent: tuple[int, int, int]


CARD_INFO = {
    PowerType.SHIELD: CardInfo("SHIELD", ("Protects all", "your tokens", "for 2 turns"),
                               (60, 120, 210), (24, 40, 110), (110, 210, 255)),
    PowerType.DOUBLE_DICE: CardInfo("DOUBLE DICE", ("One extra", "roll this", "turn (max 3)"),
                                    (150, 70, 200), (62, 24, 110), (255, 140, 240)),
    PowerType.SKIP: CardInfo("SKIP", ("Next player", "loses their", "whole turn"),
                             (225, 110, 60), (120, 36, 36), (255, 200, 110)),
}
CARD_ORDER = (PowerType.SHIELD, PowerType.DOUBLE_DICE, PowerType.SKIP)


class PowerEffect(ABC):
    kind: PowerType

    @abstractmethod
    def activate(self, match, player) -> tuple[str, ...]:
        """Apply the effect; return the three banner lines shown during the card animation."""
