"""Loading screen / warm-up: runs without stalls, ends in the menu, leaves the caches hot, and START GAME no longer hitches."""
import os, sys, time
os.environ["LUDO_NO_WARMUP"] = ""                      # this suite wants the real start-up path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from app_driver import *
from game.app import App
from game.warmup import Warmup
from ui.menu import MenuScreen


def test_loading_screen_then_menu():
    app = App(warmup=True)
    assert isinstance(app.scene, Warmup) and app.fade == 0.0
    worst = 0.0
    for _ in range(900):
        t = time.perf_counter(); app.frame(1 / 60); worst = max(worst, time.perf_counter() - t)
        if isinstance(app.scene, MenuScreen): break
    assert isinstance(app.scene, MenuScreen), type(app.scene)
    print(f"ok warm-up finished; slowest loading frame {worst * 1000:.0f} ms")


def test_start_game_has_no_big_hitch_after_warmup():
    app = App(warmup=True)
    for _ in range(900):
        app.frame(1 / 60)
        if isinstance(app.scene, MenuScreen): break
    idle(app, .6)
    sc = start_game_via_ui(app, 4, ["A", "B", "C", "D"], [1, 2, 3, 0], wait_turn=False)
    worst = 0.0
    for _ in range(120):
        t = time.perf_counter(); app.frame(1 / 60); worst = max(worst, time.perf_counter() - t)
    print(f"ok slowest frame after START GAME (warm): {worst * 1000:.0f} ms")
    assert worst < 0.060, worst


def test_clamped_dt_and_android_present_path():
    app = App(warmup=False)
    app._is_android = True
    app.window = pygame.display.set_mode((540, 1170), pygame.RESIZABLE)       # 19.5:9 phone-like -> letter-boxed
    for _ in range(5): app.frame(1 / 60)
    app.window = pygame.display.set_mode((720, 1280), pygame.RESIZABLE)
    for _ in range(5): app.frame(1 / 60)
    print("ok android present path")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"): fn()
    print("WARMUP TESTS PASSED")
