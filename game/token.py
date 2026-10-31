from __future__ import annotations
from dataclasses import dataclass
from game.board import STEP_YARD, STEP_FINISH


@dataclass
class Token:
    owner: int          # player / colour index
    index: int          # 0..3
    step: int = STEP_YARD

    @property
    def in_yard(self) -> bool:
        return self.step == STEP_YARD

    @property
    def finished(self) -> bool:
        return self.step == STEP_FINISH

    def reset(self) -> None:
        self.step = STEP_YARD
