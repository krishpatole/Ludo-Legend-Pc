"""Main menu / options / exit / player-count back-navigation, headless, through the real App."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_driver import *
from config.settings import SETTINGS

app = new_app(); snap(app, "40_menu"); assert app.state == S.MENU
# PLAY -> count screen -> BACK -> menu
tap(app, center(app.scene.buttons[0].rect)); assert until(app, lambda: app.state == S.PLAYER_SELECTION, 3); idle(app, .3)
snap(app, "41_select")
tap(app, center(app.scene.btn_back.rect), 0); assert until(app, lambda: app.state == S.MENU, 3)
# PLAY -> choose 3 -> names (3 fields) ; Esc walks back one step at a time
open_setup(app); choose_count(app, 3); assert app.draft.n == 3 and app.state == S.PLAYER_NAMES
idle(app, .3); snap(app, "41b_names")
press(app, pygame.K_ESCAPE); assert until(app, lambda: app.state == S.PLAYER_SELECTION, 3)
press(app, pygame.K_ESCAPE); assert until(app, lambda: app.state == S.MENU, 3)
# OPTIONS: the four toggles really flip, BACK returns
tap(app, center(app.scene.buttons[1].rect)); assert until(app, lambda: app.state == S.OPTIONS, 3); idle(app, .3)
snap(app, "42_options")
SETTINGS.bombs = True      # the harness defaults bombs OFF; start from the real default
for tg in app.scene.toggles: tap(app, center(tg.rect), 0)
assert len(app.scene.toggles) == 4
assert (SETTINGS.music, SETTINGS.sfx, SETTINGS.animations, SETTINGS.bombs) == (False, False, False, False)
for tg in app.scene.toggles: tap(app, center(tg.rect), 0)
assert (SETTINGS.music, SETTINGS.sfx, SETTINGS.animations, SETTINGS.bombs) == (True, True, True, True)
tap(app, center(app.scene.btn.rect), 0); assert until(app, lambda: app.state == S.MENU, 3)
# a full game start from the menu, then MENU button inside the game returns to the menu
sc = start_game_via_ui(app, 2, ["Asha", "Ben"], [0, 2])
tap(app, center(sc.menu_btn.rect), 0); assert until(app, lambda: app.state == S.MENU, 4)
# EXIT
tap(app, center(app.scene.buttons[2].rect), 0); assert app.running is False
print("MENU FLOW OK")
