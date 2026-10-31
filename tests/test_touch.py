"""Touch input: finger events must drive the UI exactly like a mouse, and one tap must act ONCE."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_driver import *
from config.settings import SETTINGS


def finger(app, canvas_pos, emulated_mouse=True):
    """A tap exactly as SDL reports it: FINGERDOWN/UP (+ optionally its emulated touch=True mouse events)."""
    k, (ox, oy), _ = app._viewport(); ww, wh = app.window.get_size()
    wx, wy = canvas_pos[0] * k + ox, canvas_pos[1] * k + oy
    nx, ny = wx / ww, wy / wh
    pos = (int(wx), int(wy))
    down = [pygame.event.Event(pygame.FINGERDOWN, x=nx, y=ny, dx=0, dy=0, finger_id=0, touch_id=0)]
    up = [pygame.event.Event(pygame.FINGERUP, x=nx, y=ny, dx=0, dy=0, finger_id=0, touch_id=0)]
    if emulated_mouse:
        down.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1, touch=True))
        up.append(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1, touch=True))
    app.frame(DT, down); app.frame(DT, up)
    for _ in range(3): app.frame(DT)


for emu in (True, False):                       # SDL with and without touch->mouse emulation
    app = new_app()
    finger(app, center(app.scene.buttons[1].rect), emu); idle(app, .6)                 # OPTIONS
    assert app.state == S.OPTIONS, (emu, app.state)
    before = SETTINGS.sfx
    finger(app, center(app.scene.toggles[1].rect), emu)                                 # SFX toggle: flips exactly once
    assert SETTINGS.sfx == (not before), ("double-fired tap", emu)
    finger(app, center(app.scene.toggles[1].rect), emu); assert SETTINGS.sfx == before
    finger(app, center(app.scene.btn.rect), emu); idle(app, .6); assert app.state == S.MENU
    # whole setup wizard by finger
    finger(app, center(app.scene.buttons[0].rect), emu); idle(app, .6); assert app.state == S.PLAYER_SELECTION
    idle(app, .4); finger(app, center(next(c["rect"] for c in app.scene.cards if c["n"] == 4)), emu); idle(app, .6)
    assert app.state == S.PLAYER_NAMES and app.draft.n == 4
    finger(app, center(app.scene.field_rect(2)), emu); type_text(app, "Zoe"); assert app.draft.names[2] == "Zoe"   # focus by tap
    finger(app, center(app.scene.btn_next.rect), emu); idle(app, .6); assert app.state == S.COLOR_SELECTION
    sc = app.scene
    finger(app, center(sc.tile_rect(0, 2)), emu); assert app.draft.colours[0] == 2                              # exactly one pick
    finger(app, center(sc.tile_rect(1, 2)), emu); assert app.draft.colours[1] is None                          # locked colour
    finger(app, center(sc.btn_auto.rect), emu); assert app.draft.colours_complete
    finger(app, center(sc.btn_next.rect), emu); idle(app, .6); assert app.state == S.SETUP_REVIEW
    finger(app, center(app.scene.btn_start.rect), emu); idle(app, .6)
    assert until(app, lambda: isinstance(app.scene, GameScene) and app.scene.state == S.PLAYER_TURN, 12)
    sc = app.scene; cur = sc.cur
    other = center(sc.dices[[c for c in sc.order if c != cur][0]].rect)
    finger(app, other, emu); assert sc.state == S.PLAYER_TURN and sc.match.turn.rolls_taken == 0   # not their dice
    sc.match.dice.force(6); finger(app, center(sc.dices[cur].rect), emu)
    assert sc.match.turn.rolls_taken == 1, (emu, "dice tap should roll exactly once")
    while sc.state not in (S.TOKEN_SELECTION, S.TOKEN_MOVEMENT): app.frame(DT)
    if sc.state == S.TOKEN_SELECTION:              # four yard tokens are equivalent -> may auto-play; else tap one
        finger(app, tok_pos(sc, cur, sc.selectable[0].index), emu)
    while sc.state != S.PLAYER_TURN: app.frame(DT)            # a 6 gives a bonus roll -> back to PLAYER_TURN
    assert any(t.step == 0 for t in sc.match.players[cur].tokens), "token did not leave the yard"
    assert sc.match.turn.rolls_remaining == 1 and sc.cur == cur
    print(f"ok touch (emulated mouse events {'on' if emu else 'off'})")
print("TOUCH OK")
