"""Central configuration: sizes, colours, timings and user settings."""
from dataclasses import dataclass

TITLE = "LUDO LEGENDS"
TAGLINE = "ROLL • STRATEGIZE • DOMINATE"
WIDTH, HEIGHT = 1366, 768
FPS = 60

CELL = 28
BOARD_SIZE = CELL * 15
BOARD_X = (WIDTH - BOARD_SIZE) // 2
BOARD_Y = (HEIGHT - BOARD_SIZE) // 2

PLAYER_NAMES = ("PLAYER 1", "PLAYER 2", "PLAYER 3", "PLAYER 4")
PLAYER_COLORS = ((222, 66, 66), (52, 178, 96), (62, 118, 226), (244, 194, 44))
PLAYER_COLOR_NAMES = ("Red", "Green", "Blue", "Yellow")

# Player zone: name row -> token row -> power-card row
ZONE_W, ZONE_H = 240, 156
CARD_W, CARD_H = 72, 100
CARD_GAP = 6
TOKEN_R = 10
MAX_CARDS_PER_TURN = 1   # one power card per turn (set higher to allow combos)

GOLD = (236, 192, 92)
GOLD_LIGHT = (255, 227, 150)
GOLD_DARK = (150, 106, 40)
WHITE = (245, 247, 255)
INK = (16, 18, 36)
CYAN = (90, 220, 255)

# Timings (seconds)
T_FIRST_CYCLE = 2.2
T_FIRST_TOTAL = 3.6
T_DICE = 0.9
T_STEP = 0.17
T_ENTER = 0.4
T_POWER = 2.4
T_CAPTURE = 1.0
T_SKIP = 1.5
T_NEXT = 0.45
T_NO_MOVE = 1.0
T_AUTO_MOVE = 0.45
T_BOMB_WARN = 3.0        # marked squares flash red this long before the bomb explodes
T_BOMB_BLAST = 1.7       # explosion + tokens flying home

HOME_STEPS = 56          # token steps: -1 yard, 0..50 ring, 51..55 lane, 56 finished
MAX_DOUBLE_ROLLS = 3
SHIELD_TURNS = 2


@dataclass
class Settings:
    music: bool = True
    sfx: bool = True
    animations: bool = True
    bombs: bool = True       # the 4 hidden-timer bombs per game

    def dur(self, seconds: float) -> float:
        """Scale a duration; animations OFF makes everything much snappier."""
        return seconds if self.animations else seconds * 0.35


SETTINGS = Settings()
