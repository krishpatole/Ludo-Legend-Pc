"""Headless harness that drives the real GameScene with synthetic clicks (used by tests + manual review)."""
import os, sys
os.environ.setdefault("LUDO_NO_WARMUP", "1")      # tests build scenes directly; test_warmup.py covers the loading screen
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
pygame.init()
from config.settings import *
from game.states import GameState as S
from ui.game_ui import GameScene
from ui import layout as L

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
_mouse = [(0, 0)]
pygame.mouse.get_pos = lambda: _mouse[0]
# Bombs are random board events; scripted tests turn them OFF so positions stay predictable.
# Tests that cover bombs switch them on explicitly.
from config.settings import SETTINGS as _S
_S.bombs = False
SHOTS = os.environ.get("SHOTS", "/tmp/claude-0/-home-claude/1f8a9acf-a081-5b33-bd0f-9c153d6528f6/scratchpad/shots")


def move_mouse(pos): _mouse[0] = pos


def step(sc, seconds=0.0, until=None, limit=30.0):
    """Advance the scene at 60 FPS for `seconds`, or until a predicate holds."""
    t = 0.0
    while True:
        if until is not None and until(): return True
        if until is None and t >= seconds: return True
        if t >= (limit if until is not None else seconds + 1): return False
        sc.update(1 / 60); t += 1 / 60
    

def draw(sc): sc.draw(SCREEN)


def shot(sc, name):
    draw(sc); pygame.image.save(SCREEN, os.path.join(SHOTS, name + ".png"))


def click(sc, pos):
    move_mouse(pos)
    sc.update(1 / 60)
    sc.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    sc.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))


def new_scene(n=4, exits=None):
    sc = GameScene(n, (exits.append if exits is not None else (lambda x: None)))
    return sc


def to_turn(sc, first=None):
    if first is not None: sc.first = first
    assert step(sc, until=lambda: sc.state == S.PLAYER_TURN, limit=10)


def card_pos(sc, seat, kind):
    for cv in sc.hands[seat]:
        if cv.kind == kind: return (int(cv.x), int(cv.y))
    raise KeyError(kind)


def do_roll(sc, value):
    sc.match.dice.force(value)
    click(sc, dice_pos(sc))


def dice_pos(sc, seat=None):
    return tuple(int(v) for v in L.dice_center(sc.cur if seat is None else seat))
