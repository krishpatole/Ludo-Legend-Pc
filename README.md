# 👑 LUDO LEGENDS
**ROLL • STRATEGIZE • DOMINATE** — a local-multiplayer Ludo game with power cards, written in Python + Pygame.

## Features
- 2, 3 or 4 players (Red, Green, Blue, Yellow), 4 tokens each, standard Ludo rules
- **Every player has their own dice**, next to their own zone (only the current player's dice is clickable)
- **Setup wizard:** Main Menu → Player count (2/3/4) → **Custom names** → **Unique colours** → Review → Start Game (Back / Continue at every step, edit anything before starting)
- Names and colours show up on the board yards, player zones, turn panel, banners and the victory screen; long names are shortened to fit (max 14 characters)
- **Bombs:** exactly 4 per game, on a hidden game-progress timer (see Bombs below); Options → BOMBS ON/OFF
- **Capture bonus:** capturing an opponent earns you one extra roll
- Per-player zone: **name → 4 tokens → 3 power cards**; each player owns an independent set of cards
- Power cards: **Shield**, **Double Dice**, **Skip** — click the card itself (no popups)
- Step-by-step token animation, capture/shield-block effects, first-player draw, victory screen, options (music / SFX / animations)
- Fixed 1366x768 canvas that scales (letter-boxed) to any window or screen; mouse **and** touch input

## Requirements
Python 3.9 or newer and `pygame` 2.5+. Tested on Python **3.10.20** and 3.13 with pygame 2.6.1 (Linux, headless and on a virtual X11 display).

## Setup and run — Windows
Open **Command Prompt** (cmd) in the project folder:
```
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
Quicker, without a virtual environment:
```
py -3 -m pip install -r requirements.txt
py -3 main.py
```
(PowerShell: if `activate` is blocked, run `Set-ExecutionPolicy -Scope Process Bypass` first, or just use cmd.)

## Setup and run — Linux / macOS
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Controls
Mouse click or finger tap on everything. `F11` toggles fullscreen. `Esc` (Android Back button) goes back / to the menu.

## Game setup
1. **Players** – pick 2, 3 or 4.
2. **Names** – type a name per player (empty box = "Player 1", "Player 2", …). Tab / Enter jumps to the next box; names must be different.
3. **Colours** – every player picks Red, Green, Blue or Yellow. A colour held by someone else is locked (dimmed, marked TAKEN);
   click your own colour again to release it. **Auto assign** fills the rest.
4. **Review** – check the line-up (turn order is clockwise around the board), go back to edit, then **Start Game**.

A colour is also the board corner: Red = left, Green = top, Blue = right, Yellow = bottom (own yard, start square and home lane).
On this board the opposite corners are **Red–Blue** and **Green–Yellow** (checked from the board geometry in `tests/test_setup.py`),
so in a **2-player** game picking one colour automatically gives the other player its opposite colour.
Play Again keeps the same names and colours; Main Menu → Play lets you change them.

## Game rules
- A 6 brings a token out of the yard; a played 6 gives a bonus roll.
- An exact roll is needed to enter the centre. Landing on an opponent (not on a ★ safe cell or a start cell) sends it home.
- No valid move → the turn passes automatically. Only one distinct move → it is played automatically.
- **Capture bonus:** a legal capture gives the capturing player one extra roll (once per capturing move, even if several tokens were captured).
  No bonus for landing on a safe square, for a capture blocked by a Shield, or for the captured player.
  A capture and a 6 on the same move stack (two extra rolls). During a Double Dice turn the total is still capped at 3 rolls.
- First player to bring all 4 tokens home wins.

## Bombs
- Every game has **exactly 4 bombs**. The timer is hidden: it follows how close the leading player is to winning
  (roughly at 20 %, 40 %, 60 % and 80 % of the way, each shifted randomly by up to 4 %, so you cannot predict it). All four always fall before anyone can win.
- At the end of a turn the game flashes **3-5 random squares red** (with a bomb icon, 3 seconds of warning, nobody can move meanwhile) and then they explode.
- Every token standing on a bombed square is **sent back to its yard**. Safe stars, start squares, home lanes and the yard are never bombed.
- A **Shield** protects its owner's tokens from bombs too ("SHIELD BLOCKED THE BOMB!").
- A bomb never gives anyone a bonus roll and never changes whose turn is next. The top panel shows `BOMBS 1/4`.
- Turn off in Options → BOMBS.

## Power cards (one per turn, only BEFORE rolling, consumed when used)
| Card | Effect |
|---|---|
| Shield | None of your tokens can be captured during your next 2 turns (counter shown) |
| Double Dice | One extra roll this turn. 6s still give bonus rolls, but the turn is capped at **3 rolls** |
| Skip | The next player's whole turn is skipped; you still play your own turn |

## Tests (all headless — no window or sound device needed)
```
python run_tests.py            # every suite below (about 1-2 minutes)
python run_tests.py --soak     # additionally plays complete bot games through the whole wizard (slow)
```
| Suite | Covers |
|---|---|
| `tests/test_logic.py` | core rules: 6s, exact finish, capture, safe squares, shield, skip, Double Dice cap, win |
| `tests/test_capture_bonus.py` | capture bonus: capturer gets it, none on safe squares / shield blocks, +6 stacking, multi-capture, Double Dice cap, skip/shield, win, fresh state |
| `tests/test_bombs.py` | exactly 4 bombs in 75 simulated games, hidden jittered timer, 3-5 non-safe squares, shield immunity, no bonus roll, live warning/explosion flow |
| `tests/test_setup.py` | opposite corners from the real geometry, unique colours, name cleaning, every legal colour layout plays full games |
| `tests/test_setup_ui.py` | the whole wizard by clicking/typing, long names, no-overlap check for 7 layouts, status box gone, text input released |
| `tests/test_ui_flow.py`, `test_menus.py`, `test_scaling.py`, `test_touch.py` | cards, captures, victory, menus, window scaling, touch input |

Single suite: `python tests/test_capture_bonus.py` etc. Soak: `python tests/test_soak.py <players 2|3|4> <seed> <animations 0|1>`.

## Build
Kept separate on purpose:
- **Windows `.exe`** → [docs/BUILD_WINDOWS.md](docs/BUILD_WINDOWS.md) (`build_windows.bat`, `LudoLegends.spec`)
- **Android `.apk`** → [docs/BUILD_ANDROID.md](docs/BUILD_ANDROID.md) (`buildozer.spec`)

Neither a real `.exe` nor an `.apk` has been produced yet, and nothing has been tested on a real phone. See those files for status.

## Audio
Sounds are synthesised when no files exist. To use your own, put `click, dice, move, capture, shield, shield_block, skip, double, bonus, home, victory, card` and `music` (`.ogg` / `.wav` / `.mp3`) into `assets/sounds/`. Missing audio or no sound device never crashes the game.

## Project structure
```
main.py                entry point (DPI awareness, crash log)
run_tests.py           runs every test suite
game/                  app.py (window, scaling, input, scene switching), game.py (Match), rules, board, turn_manager, dice, player, token, states
powers/                power_card, shield, double_dice, skip
ui/                    menu, player_selection, game_ui (state machine), cards, dice_view, board_view, buttons, animations, victory, layout
audio/ config/ utils/  audio manager, settings, helpers
tests/                 headless tests
docs/                  BUILD_WINDOWS.md, BUILD_ANDROID.md
```

## Troubleshooting
- `ModuleNotFoundError: pygame` → run the `pip install -r requirements.txt` step inside the same environment you run `python main.py` from.
- Window too large for a small screen → it shrinks automatically; resize freely or press `F11`.
- Crash in the built `.exe` → read `ludo_legends_crash.log` next to the exe.

## Future improvements
Online multiplayer, AI players, more power cards, themes, saved settings, portrait phone layout.
