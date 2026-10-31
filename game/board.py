"""Board geometry: the 52-cell ring, home lanes, yards, safe cells.

Token ``step`` convention (per player, relative to their own start cell):
    -1        in the yard
    0..50     on the shared ring (step 0 == the player's start cell)
    51..55    on the player's private home lane
    56        finished (centre)
Grid coordinates are (col, row) on a 15x15 grid.
"""
from __future__ import annotations
from config.settings import CELL, BOARD_X, BOARD_Y

RING = [
    (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 5), (6, 4), (6, 3), (6, 2), (6, 1), (6, 0),
    (7, 0), (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (9, 6), (10, 6), (11, 6), (12, 6),
    (13, 6), (14, 6), (14, 7), (14, 8), (13, 8), (12, 8), (11, 8), (10, 8), (9, 8), (8, 9),
    (8, 10), (8, 11), (8, 12), (8, 13), (8, 14), (7, 14), (6, 14), (6, 13), (6, 12), (6, 11),
    (6, 10), (6, 9), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8), (0, 7), (0, 6),
]
assert len(RING) == 52 and len(set(RING)) == 52

RING_LEN = 52
START_OFFSET = (0, 13, 26, 39)                       # ring index of each colour's start
SAFE_RING = frozenset({0, 8, 13, 21, 26, 34, 39, 47})  # starts + stars
LANES = (
    [(1, 7), (2, 7), (3, 7), (4, 7), (5, 7)],        # red   (left)
    [(7, 1), (7, 2), (7, 3), (7, 4), (7, 5)],        # green (top)
    [(13, 7), (12, 7), (11, 7), (10, 7), (9, 7)],    # blue  (right)
    [(7, 13), (7, 12), (7, 11), (7, 10), (7, 9)],    # yellow(bottom)
)
YARD_ORIGIN = ((0, 0), (9, 0), (9, 9), (0, 9))       # top-left cell of each 6x6 yard
HOME_DIR = ((-1, 0), (0, -1), (1, 0), (0, 1))        # direction from centre toward each colour

STEP_YARD, STEP_START, STEP_RING_END, STEP_FINISH = -1, 0, 50, 56


def ring_index(color: int, step: int) -> int:
    return (START_OFFSET[color] + step) % RING_LEN


def is_on_ring(step: int) -> bool:
    return STEP_START <= step <= STEP_RING_END


def is_safe_step(color: int, step: int) -> bool:
    return is_on_ring(step) and ring_index(color, step) in SAFE_RING


def yard_slot(color: int, slot: int) -> tuple[float, float]:
    """Continuous grid coords of a yard socket (centre of the 6x6 yard +/- 1)."""
    ox, oy = YARD_ORIGIN[color]
    return ox + 3 + (-1 if slot % 2 == 0 else 1), oy + 3 + (-1 if slot < 2 else 1)


def grid_pos(color: int, step: int, slot: int = 0) -> tuple[float, float]:
    """Continuous grid coords (cell centres are +0.5) for a token at ``step``."""
    if step < 0:
        return yard_slot(color, slot)
    if step <= STEP_RING_END:
        c, r = RING[ring_index(color, step)]
        return c + 0.5, r + 0.5
    if step < STEP_FINISH:
        c, r = LANES[color][step - 51]
        return c + 0.5, r + 0.5
    dx, dy = HOME_DIR[color]
    off = (slot - 1.5) * 0.34
    return 7.5 + dx * 0.85 - dy * off, 7.5 + dy * 0.85 + dx * off


def to_px(gx: float, gy: float) -> tuple[float, float]:
    return BOARD_X + gx * CELL, BOARD_Y + gy * CELL


def token_px(color: int, step: int, slot: int = 0) -> tuple[float, float]:
    return to_px(*grid_pos(color, step, slot))
