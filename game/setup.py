"""Pre-game setup: player count, custom names and unique board colours.

Pure Python (no pygame) so every rule here is unit-testable. A colour id (0 Red, 1 Green, 2 Blue,
3 Yellow) IS the board position: it decides the player's yard, start square, home lane and zone.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

from game.board import START_OFFSET, RING_LEN

MIN_PLAYERS, MAX_PLAYERS = 2, 4
MAX_NAME_LEN = 14
COLOUR_NAMES = ("Red", "Green", "Blue", "Yellow")
SEAT_NAMES = ("Left", "Top", "Right", "Bottom")           # where each colour's zone sits on screen
DEFAULT_COLOURS = {2: (0, 2), 3: (0, 1, 2), 4: (0, 1, 2, 3)}


class SetupError(ValueError):
    """The chosen setup is not a legal game."""


def _opposite(colour: int) -> int:
    """The colour whose start square is half a lap (26 cells) away == the opposite corner.
    Derived from the board itself (see tests: the start cells are point mirrors of each other)."""
    target = (START_OFFSET[colour] + RING_LEN // 2) % RING_LEN
    return next(c for c, off in enumerate(START_OFFSET) if off == target)


OPPOSITE = tuple(_opposite(c) for c in range(4))          # (2, 3, 0, 1): Red<->Blue, Green<->Yellow


def default_name(i: int) -> str:
    return f"Player {i + 1}"


def short_tag(name: str) -> str:
    """Tiny label for a circle: 'Player 2' -> 'P2', 'Krish Patole' -> 'KP', 'Zoe' -> 'ZO'."""
    words = name.split()
    if len(words) >= 2 and words[0].casefold() == "player" and words[-1].isdigit():
        return "P" + words[-1]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return name[:2].upper()


def clean_name(raw: str | None, i: int) -> str:
    """Strip control characters, collapse whitespace, cap the length; empty -> default name."""
    s = re.sub(r"[\t\n\r\v\f]", " ", raw or "")             # whitespace controls act like spaces
    s = re.sub(r"[\x00-\x1f\x7f]", "", s)                    # any other control character is dropped
    s = " ".join(s.split())[:MAX_NAME_LEN].strip()
    return s or default_name(i)


@dataclass(frozen=True)
class PlayerSetup:
    name: str
    colour: int


@dataclass(frozen=True)
class GameSetup:
    players: tuple[PlayerSetup, ...]

    @property
    def n(self) -> int:
        return len(self.players)

    @property
    def colours(self) -> tuple[int, ...]:
        return tuple(p.colour for p in self.players)

    @property
    def turn_order(self) -> tuple[int, ...]:
        """Clockwise around the board (Red left -> Green top -> Blue right -> Yellow bottom)."""
        return tuple(sorted(self.colours))

    @classmethod
    def default(cls, n: int) -> "GameSetup":
        colours = DEFAULT_COLOURS[n]
        return cls.create([default_name(i) for i in range(n)], colours)

    @classmethod
    def create(cls, names, colours) -> "GameSetup":
        names = [clean_name(nm, i) for i, nm in enumerate(names)]
        errors = validate(names, list(colours))
        if errors:
            raise SetupError("; ".join(errors))
        return cls(tuple(PlayerSetup(nm, int(c)) for nm, c in zip(names, colours)))


def validate(names, colours) -> list[str]:
    errors: list[str] = []
    n = len(colours)
    if not (MIN_PLAYERS <= n <= MAX_PLAYERS) or len(names) != n:
        return [f"{MIN_PLAYERS}-{MAX_PLAYERS} players required"]
    if any(c is None or not isinstance(c, int) or not 0 <= c < 4 for c in colours):
        return ["every player needs a colour"]
    if len(set(colours)) != n:
        errors.append("two players cannot share a colour")
    elif n == 2 and OPPOSITE[colours[0]] != colours[1]:
        errors.append("2 players must sit on opposite corners (Red-Blue or Green-Yellow)")
    lowered = [nm.casefold() for nm in names]
    if len(set(lowered)) != n:
        errors.append("player names must be different")
    return errors


class SetupDraft:
    """Mutable state behind the setup screens (count -> names -> colours -> review)."""

    def __init__(self, n: int = 4):
        self.n = n
        self.names: list[str] = [""] * MAX_PLAYERS              # raw text; '' means "use the default"
        self.colours: list[int | None] = [None] * MAX_PLAYERS

    # ---- step 1 ----------------------------------------------------------
    def set_count(self, n: int) -> None:
        if not MIN_PLAYERS <= n <= MAX_PLAYERS:
            raise SetupError("player count must be 2, 3 or 4")
        if n != self.n:
            self.colours = [None] * MAX_PLAYERS                  # the colour rules differ per count
        self.n = n

    # ---- step 2 ----------------------------------------------------------
    def set_name(self, i: int, text: str) -> None:
        self.names[i] = text[:MAX_NAME_LEN]

    def display_names(self) -> list[str]:
        return [clean_name(self.names[i], i) for i in range(self.n)]

    def name_errors(self) -> list[str]:
        names = self.display_names()
        return ["Player names must be different"] if len({x.casefold() for x in names}) != len(names) else []

    # ---- step 3 ----------------------------------------------------------
    def _others(self, i: int) -> list[int]:
        return [j for j in range(self.n) if j != i]

    def taken_by(self, i: int, colour: int) -> int | None:
        """Index of another player already holding this colour, else None."""
        for j in self._others(i):
            if self.colours[j] == colour:
                return j
        return None

    def block_reason(self, i: int, colour: int) -> str | None:
        """Why player i cannot pick this colour right now (None = available)."""
        j = self.taken_by(i, colour)
        if j is not None:
            return f"Taken by {clean_name(self.names[j], j)}"
        return None

    def pick_colour(self, i: int, colour: int) -> bool:
        """Select a colour for player i. Clicking your own colour again un-selects it.
        2 players always sit opposite each other, so a pick also assigns the opposite colour to the other."""
        if not 0 <= i < self.n or not 0 <= colour < 4:
            return False
        if self.colours[i] == colour:
            self.colours[i] = None
            return True
        if self.block_reason(i, colour) is not None:
            return False
        self.colours[i] = colour
        if self.n == 2:
            self.colours[1 - i] = OPPOSITE[colour]
        return True

    def auto_assign(self) -> None:
        """Fill in every player who has no colour yet with the first legal one."""
        for i in range(self.n):
            if self.colours[i] is None:
                for c in range(4):
                    if self.block_reason(i, c) is None and self.pick_colour(i, c):
                        break

    @property
    def colours_complete(self) -> bool:
        return all(self.colours[i] is not None for i in range(self.n))

    # ---- step 4 ----------------------------------------------------------
    def build(self) -> GameSetup:
        return GameSetup.create(self.display_names(), self.colours[: self.n])
