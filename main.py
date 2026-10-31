"""LUDO LEGENDS - entry point.

Run:   python main.py          (Windows: py main.py)
"""
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _enable_windows_dpi_awareness() -> None:
    """Stop Windows from bitmap-stretching (blurring) the window on 125%/150% display scaling."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _log_crash() -> str:
    """A windowed .exe has no console, so write the traceback next to the game for bug reports."""
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else ROOT
    path = os.path.join(base, "ludo_legends_crash.log")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
    except OSError:
        path = "(could not write crash log)"
    return path


def main() -> int:
    _enable_windows_dpi_awareness()
    try:
        from game.app import App
        App().run()
    except SystemExit:
        raise
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        print("Crash log:", _log_crash(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
