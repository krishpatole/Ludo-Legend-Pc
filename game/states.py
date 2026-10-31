"""Application / match state machine states."""
from enum import Enum, auto


class GameState(Enum):
    MENU = auto()
    PLAYER_SELECTION = auto()
    PLAYER_NAMES = auto()
    COLOR_SELECTION = auto()
    SETUP_REVIEW = auto()
    OPTIONS = auto()
    DETERMINING_FIRST_PLAYER = auto()
    PLAYER_TURN = auto()          # waiting for card click or dice click
    POWER_ANIMATION = auto()      # card flying to centre
    DICE_ROLLING = auto()
    NO_MOVE = auto()              # rolled, but nothing can move
    TOKEN_SELECTION = auto()
    TOKEN_MOVEMENT = auto()
    CAPTURE_ANIMATION = auto()
    NEXT_TURN = auto()
    BOMB_WARNING = auto()         # bomb squares flash red
    BOMB_EXPLOSION = auto()       # bang + tokens fly home
    TURN_SKIPPED = auto()
    VICTORY = auto()
