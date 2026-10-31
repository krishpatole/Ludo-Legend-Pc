"""Run every headless test.   python run_tests.py   (exit code 0 = all passed)

The soak test plays full bot games and is slow; it is only run with:  python run_tests.py --soak
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SUITES = ["test_logic.py", "test_setup.py", "test_capture_bonus.py", "test_ui_flow.py", "test_setup_ui.py",
          "test_bombs.py", "test_menus.py", "test_scaling.py", "test_touch.py"]
if "--soak" in sys.argv:
    SUITES.append("test_soak.py")

env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYTHONIOENCODING="utf-8")
failed = []
for name in SUITES:
    print(f"=== {name}", flush=True)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", name)], env=env, cwd=ROOT)
    if r.returncode != 0:
        failed.append(name)
print("\nFAILED: " + ", ".join(failed) if failed else "\nALL TEST SUITES PASSED")
sys.exit(1 if failed else 0)
