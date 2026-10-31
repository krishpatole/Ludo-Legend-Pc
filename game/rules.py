"""Pure Ludo rules: move validity, landing resolution, captures."""
from __future__ import annotations
from dataclasses import dataclass, field
from game.board import (STEP_FINISH, STEP_START, STEP_RING_END, ring_index, is_on_ring,
                        is_safe_step)
from game.token import Token
from game.player import Player


@dataclass
class MoveResult:
    token: Token
    from_step: int
    to_step: int
    path: list[int] = field(default_factory=list)       # every step visited, in order
    captured: list[Token] = field(default_factory=list)
    blocked: list[Token] = field(default_factory=list)  # protected by a shield
    left_yard: bool = False
    reached_home: bool = False


def target_step(token: Token, dice: int) -> int | None:
    """Destination step for this roll, or None if the move is illegal."""
    if token.in_yard:
        return STEP_START if dice == 6 else None
    if token.finished:
        return None
    new = token.step + dice
    return new if new <= STEP_FINISH else None      # exact roll needed to finish


def valid_tokens(player: Player, dice: int) -> list[Token]:
    return [t for t in player.tokens if target_step(t, dice) is not None]


def opponents_on_ring_cell(players: list[Player], mover: int, ring_idx: int) -> list[Token]:
    out = []
    for p in players:
        if p.index == mover:
            continue
        out += [t for t in p.tokens if is_on_ring(t.step) and ring_index(p.index, t.step) == ring_idx]
    return out


def apply_move(token: Token, dice: int, players: list[Player]) -> MoveResult:
    dest = target_step(token, dice)
    assert dest is not None, "illegal move"
    res = MoveResult(token, token.step, dest)
    res.left_yard = token.in_yard
    res.path = [dest] if token.in_yard else list(range(token.step + 1, dest + 1))
    token.step = dest
    res.reached_home = dest == STEP_FINISH
    # Landing on a non-safe ring cell captures every unshielded opponent token there.
    if is_on_ring(dest) and not is_safe_step(token.owner, dest):
        for foe in opponents_on_ring_cell(players, token.owner, ring_index(token.owner, dest)):
            if players[foe.owner].shielded:
                res.blocked.append(foe)
            else:
                foe.reset()
                res.captured.append(foe)
    return res
