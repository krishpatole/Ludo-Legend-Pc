"""Match: the pure (pygame-free) game model that ties players, dice, rules and powers."""
from __future__ import annotations
import random
from config.settings import MAX_CARDS_PER_TURN
from game.bombs import BombScheduler, BombResult
from game.dice import Dice
from game.player import Player
from game.setup import GameSetup
from game.rules import MoveResult, apply_move, valid_tokens
from game.token import Token
from game.turn_manager import TurnManager, TurnEnd
from powers import EFFECTS, PowerType


class Roster:
    """The participating players in clockwise turn order, indexed by BOARD COLOUR id.

    ``roster[2]`` is the player sitting on the Blue corner (whoever they are); iterating yields the
    players in turn order and ``len`` is the player count. Colours that are not playing raise KeyError.
    """

    def __init__(self, players):
        players = sorted(players, key=lambda p: p.index)
        self._by_colour = {p.index: p for p in players}
        self._order = [p.index for p in players]

    def __getitem__(self, colour: int) -> Player:
        try:
            return self._by_colour[colour]
        except KeyError:
            raise KeyError(f"no player is using colour {colour}") from None

    def __iter__(self):
        return (self._by_colour[c] for c in self._order)

    def __len__(self) -> int:
        return len(self._order)

    def __contains__(self, colour) -> bool:
        return colour in self._by_colour

    @property
    def colours(self) -> list[int]:
        return list(self._order)


class Match:
    def __init__(self, setup: "GameSetup | int", seed: int | None = None):
        if isinstance(setup, int):                       # convenience for tests: default names/colours
            setup = GameSetup.default(setup)
        self.setup = setup
        self.rng = random.Random(seed)
        self.dice = Dice(None if seed is None else seed + 1)
        self.players = Roster(Player(ps.colour, ps.name) for ps in setup.players)
        self.turn = TurnManager(self.players.colours)
        self.last_roll = 0
        self.winner: int | None = None
        # own RNG so bombs never disturb the dice / first-player sequence of a seeded match
        self.bombs = BombScheduler(random.Random(None if seed is None else seed + 7))
        self.res_bonus: list[str] = []                  # bonus rolls granted by the last move: 'six' / 'capture'

    # ---- basics ----------------------------------------------------------
    @property
    def current(self) -> Player:
        return self.players[self.turn.current]

    def pick_first_player(self) -> int:
        """Colour id of the player who starts."""
        return self.rng.choice(self.players.colours)

    def start(self, first: int) -> None:
        self.turn.begin_turn(first)

    # ---- power cards -----------------------------------------------------
    def can_use_card(self, player_idx: int, kind: PowerType) -> bool:
        t = self.turn
        return (self.winner is None and player_idx == t.current and t.rolls_taken == 0
                and t.cards_used < MAX_CARDS_PER_TURN and self.players[player_idx].has_card(kind))

    def use_card(self, player_idx: int, kind: PowerType) -> tuple[str, ...]:
        if not self.can_use_card(player_idx, kind):
            raise ValueError("card cannot be used now")
        p = self.players[player_idx]
        p.remove_card(kind)                 # consumed immediately -> double clicks are harmless
        self.turn.cards_used += 1
        return EFFECTS[kind].activate(self, p)

    # ---- dice / moves ------------------------------------------------------
    @property
    def can_roll(self) -> bool:
        return self.winner is None and self.turn.can_roll

    def roll(self) -> int:
        if not self.can_roll:
            raise ValueError("cannot roll")
        self.turn.on_roll()
        self.res_bonus = []
        self.last_roll = self.dice.roll()
        return self.last_roll

    def valid_tokens(self) -> list[Token]:
        return valid_tokens(self.current, self.last_roll)

    def move(self, token: Token) -> MoveResult:
        assert token in self.valid_tokens()
        res = apply_move(token, self.last_roll, self.players)
        if self.current.has_won:
            self.winner = self.current.index
        # one capture bonus per capturing MOVE (not per captured token), to the player who moved
        self.res_bonus = self.turn.finish_roll(self.last_roll, True, captured=bool(res.captured))
        if self.winner is not None:                      # game over: no further rolls, whatever was earned
            self.turn.rolls_remaining = 0
            self.res_bonus = []
        return res

    def no_move(self) -> None:
        self.res_bonus = self.turn.finish_roll(self.last_roll, False)

    # ---- bombs (checked by the UI at turn boundaries) -----------------------
    def bomb_due(self) -> bool:
        return self.winner is None and self.bombs.due(self.players)

    def arm_bomb(self) -> list[int]:
        return self.bombs.arm()

    def detonate_bomb(self) -> BombResult:
        return self.bombs.detonate(self.players)

    def end_turn(self) -> TurnEnd:
        info = self.turn.end_turn(self.players)
        self.turn.begin_turn(info.next_player)
        return info
