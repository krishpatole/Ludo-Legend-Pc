"""GameScene: renders the match and drives it through the GameState machine."""
from __future__ import annotations
import math
from collections import defaultdict
import pygame
from config.settings import *
from audio.audio_manager import get_audio
from game.game import Match
from game.setup import GameSetup, short_tag
from game.board import token_px, ring_index, is_on_ring, STEP_YARD, STEP_FINISH, YARD_ORIGIN
from game.rules import MoveResult, target_step
from game.states import GameState as S
from powers.power_card import PowerType, CARD_ORDER, CARD_INFO
from ui import layout as L
from ui.animations import ParticleSystem, Banner, Shake
from ui.board_view import board_surface, token_sprite, MARGIN
from ui.bomb_fx import BlastFX, draw_danger_cells, draw_danger_icons, draw_bomb_icon, ring_cell_rect
from ui.buttons import Button
from ui.cards import CardView, CardFlight, draw_card_icon
from ui.dice_view import DiceView
from ui.victory import VictoryOverlay
from utils.helpers import (draw_text, draw_text_fit, draw_glow, shade, lerp, lerp_color, approach, ease_in_out, clamp,
                           get_background, crown_surface, ease_out_back)

STEP_HOP = 9


class TokenView:
    def __init__(self, token):
        self.token = token
        self.x, self.y = token_px(token.owner, token.step, token.index)
        self.ox = self.oy = 0.0
        self.scale = 1.0
        self.hop = 0.0
        self.moving = False
        self.cell_key = self.logic_key()

    def logic_key(self):
        t = self.token
        if t.in_yard:
            return ("yard", t.owner, t.index)
        if t.finished:
            return ("home", t.owner, t.index)
        if is_on_ring(t.step):
            return ("ring", ring_index(t.owner, t.step))
        return ("lane", t.owner, t.step)

    @property
    def pos(self):
        return self.x + self.ox, self.y + self.oy - self.hop


class MoveAnim:
    """Moves a token step by step along waypoints with a little hop per step."""

    def __init__(self, view, pts, step_time, on_step):
        self.view, self.pts, self.st, self.on_step = view, pts, max(.05, step_time), on_step
        self.i, self.t, self.start = 0, 0.0, (view.x, view.y)
        view.moving = True

    def update(self, dt) -> bool:
        v = self.view
        self.t += dt
        while self.i < len(self.pts) and self.t >= self.st:
            self.t -= self.st
            self.start = self.pts[self.i]
            self.i += 1
            self.on_step(self.i, len(self.pts))
        if self.i >= len(self.pts):
            v.x, v.y = self.pts[-1]
            v.hop = 0
            v.moving = False
            return True
        k = self.t / self.st
        a, b = self.start, self.pts[self.i]
        e = ease_in_out(k)
        v.x, v.y = lerp(a[0], b[0], e), lerp(a[1], b[1], e)
        v.hop = math.sin(math.pi * k) * STEP_HOP
        return False


class ReturnAnim:
    """A captured token sliding back to its yard socket along an arc."""

    def __init__(self, view, dest, dur):
        self.view, self.dest, self.d, self.t = view, dest, dur, 0.0
        self.src = (view.x, view.y)
        view.moving = True

    def update(self, dt) -> bool:
        self.t += dt
        k = clamp(self.t / self.d)
        e = ease_in_out(k)
        v = self.view
        v.x, v.y = lerp(self.src[0], self.dest[0], e), lerp(self.src[1], self.dest[1], e)
        v.hop = math.sin(math.pi * k) * 26
        if k >= 1:
            v.hop, v.moving = 0, False
            return True
        return False


def stack_offsets(n):
    if n <= 1: return [(0, 0)]
    if n == 2: return [(-6, 0), (6, 0)]
    if n == 3: return [(-6, 4), (6, 4), (0, -6)]
    return [(-6, -5), (6, -5), (-6, 6), (6, 6)] + [(0, 0)] * (n - 4)


class GameScene:
    def __init__(self, setup, on_exit):
        """`setup` is a GameSetup (names + unique colours); an int means "default setup for n players"."""
        if isinstance(setup, int):
            setup = GameSetup.default(setup)
        self.setup = setup
        self.on_exit = on_exit                     # callback('menu' | 'again')
        self.audio = get_audio()
        self.match = Match(setup)
        self.order = self.match.players.colours    # participating colour ids, clockwise
        self.n = len(self.order)
        self.state = S.DETERMINING_FIRST_PLAYER
        self.state_t = 0.0
        self.t = 0.0
        self.first = self.match.pick_first_player()
        self.particles = ParticleSystem()
        self.banners: list[Banner] = []
        self.shake = Shake()
        self.dices = {c: DiceView(L.dice_center(c), L.DICE_SIZE) for c in self.order}   # one die per player
        self.menu_btn = Button(L.MENU_BTN, "MENU", "slate", 20)
        self.views = {(p.index, tk.index): TokenView(tk) for p in self.match.players for tk in p.tokens}
        self.hands: dict[int, list[CardView]] = {}
        for p in self.match.players:
            self.hands[p.index] = []
            for i, kind in enumerate(CARD_ORDER):
                x, y = L.card_slot(p.index, i, 3)
                self.hands[p.index].append(CardView(p.index, kind, (x, y)))
        self.shield_vis = defaultdict(float)
        self.expired_until: dict[int, float] = {}
        self.move_anim: MoveAnim | None = None
        self.return_anims: list[ReturnAnim] = []
        self.flight: CardFlight | None = None
        self.last_res: MoveResult | None = None
        self.selectable: list = []
        self.skip_queue: list[int] = []
        self.skip_player: int | None = None
        self.victory: VictoryOverlay | None = None
        self.cards_dirty = False
        self.mouse = (0, 0)
        self.rolling_dice = None
        self.hint = ""
        self.bomb_cells: list[int] = []          # squares marked by the bomb that is about to explode
        self.blasts = BlastFX()
        self._warn_beeps = 0

    # ---------------------------------------------------------------- state
    def set_state(self, s: S):
        self.state, self.state_t = s, 0.0

    @property
    def cur(self) -> int:
        return self.match.turn.current

    @property
    def dice(self) -> DiceView:
        """The die of the player whose turn it is."""
        return self.dices[self.cur]

    @property
    def focus(self) -> int | None:
        """Seat highlighted as 'active' in the UI."""
        if self.state == S.DETERMINING_FIRST_PLAYER:
            return None
        if self.state == S.TURN_SKIPPED:
            return self.skip_player
        return self.cur

    def color(self, i):
        return PLAYER_COLORS[i]

    def label(self, colour: int) -> str:
        """The (custom) display name of the player using this colour."""
        return self.match.players[colour].label

    def banner(self, lines, pos, color=GOLD_LIGHT, dur=1.5, size=30, sub=18):
        self.banners.append(Banner(lines, pos, color, SETTINGS.dur(dur), size, sub))

    def board_center(self):
        return BOARD_X + BOARD_SIZE / 2, BOARD_Y + BOARD_SIZE / 2

    def fx(self, pos, color, n=18, **kw):
        if SETTINGS.animations:
            self.particles.burst(pos, color, n, **kw)

    # ------------------------------------------------------------------ turn
    def begin_turn_ui(self):
        self.set_state(S.PLAYER_TURN)
        c = self.cur
        self.hint = "Play a power card, or roll the dice"

    def activate_card(self, cv: CardView):
        m = self.match
        if not m.can_use_card(cv.owner, cv.kind):
            cv.deny = .3
            return
        lines = m.use_card(cv.owner, cv.kind)
        self.hands[cv.owner].remove(cv)
        self.cards_dirty = True
        self.flight = CardFlight(cv, lines, self.color(cv.owner), SETTINGS.dur(T_POWER))
        self.flight_landed = False
        self.audio.play("card")
        self.set_state(S.POWER_ANIMATION)
        self.hint = ""

    def start_roll(self):
        m = self.match
        if not m.can_roll:
            return
        v = m.roll()
        self.rolling_dice = self.dice
        self.dice.start_roll(v, SETTINGS.dur(T_DICE))
        self.audio.play("dice")
        self.set_state(S.DICE_ROLLING)
        self.hint = ""

    def after_roll(self):
        m = self.match
        valid = m.valid_tokens()
        if not valid:
            m.no_move()
            self.banner(["NO VALID MOVE"], self.board_center(), (255, 130, 130), 1.0, 30)
            self.set_state(S.NO_MOVE)
            return
        self.selectable = valid
        self.set_state(S.TOKEN_SELECTION)
        self.hint = "Select a glowing token" if len({t.step for t in valid}) > 1 else ""

    def choose_token(self, token):
        if self.state != S.TOKEN_SELECTION or token not in self.selectable:
            return
        res = self.match.move(token)
        self.last_res = res
        self.selectable = []
        view = self.views[(token.owner, token.index)]
        if res.left_yard:
            pts = [token_px(token.owner, 0, token.index)]
            st = SETTINGS.dur(T_ENTER)
        else:
            pts = [token_px(token.owner, s, token.index) for s in res.path]
            st = SETTINGS.dur(T_STEP)
        self.move_anim = MoveAnim(view, pts, st, lambda i, n: self.audio.play("move", .7))
        self.set_state(S.TOKEN_MOVEMENT)
        self.hint = ""

    def on_move_complete(self):
        res, tk = self.last_res, self.last_res.token
        view = self.views[(tk.owner, tk.index)]
        view.cell_key = view.logic_key()
        land = view.pos
        col = self.color(tk.owner)
        if res.reached_home:
            self.audio.play("home")
            self.fx(land, GOLD_LIGHT, 26, speed=220)
            self.banner(["TOKEN HOME!"], (land[0], land[1] - 30), GOLD_LIGHT, 1.2, 24)
        if res.captured or res.blocked:
            for foe in res.captured:
                fv = self.views[(foe.owner, foe.index)]
                self.return_anims.append(ReturnAnim(fv, token_px(foe.owner, STEP_YARD, foe.index), SETTINGS.dur(.75)))
                self.fx((fv.x, fv.y), self.color(foe.owner), 22, speed=230)
            if res.captured:
                self.audio.play("capture")
                self.fx(land, (255, 255, 255), 14, speed=260)
                self.fx(land, col, 18, speed=200)
                if SETTINGS.animations:
                    self.shake.kick(7)
                self.banner(["CAPTURED!"], (land[0], land[1] - 34), (255, 120, 120), 1.2, 26)
            for foe in res.blocked:
                fv = self.views[(foe.owner, foe.index)]
                self.audio.play("shield_block")
                self.fx((fv.x, fv.y), CYAN, 24, speed=210, g=0)
                self.banner(["SHIELD BLOCKED!"], (fv.x, fv.y - 38), CYAN, 1.3, 24)
            self.set_state(S.CAPTURE_ANIMATION)
        else:
            self.after_move()

    def after_move(self):
        m = self.match
        if m.winner is not None:
            self.victory = VictoryOverlay(m.winner, self.color(m.winner), self.on_exit, self.label(m.winner))
            self.audio.play("victory")
            self.set_state(S.VICTORY)
            return
        self.continue_or_end()

    def continue_or_end(self):
        m = self.match
        if m.can_roll:
            self.set_state(S.PLAYER_TURN)
            reasons = list(m.res_bonus)
            pos = (self.board_center()[0], BOARD_Y + 40)
            if "capture" in reasons and "six" in reasons:
                self.banner(["SIX + CAPTURE!", f"{m.turn.rolls_remaining} BONUS ROLLS"], pos, GOLD_LIGHT, 1.5, 28, 18)
                self.audio.play("bonus")
            elif "capture" in reasons:
                self.banner(["CAPTURE BONUS!", "ROLL AGAIN"], pos, (255, 150, 120), 1.4, 28, 18)
                self.audio.play("bonus")
            elif "six" in reasons:
                self.banner(["BONUS ROLL!"], pos, GOLD_LIGHT, 1.2, 28)
                self.audio.play("bonus")
            else:                                          # the extra roll that Double Dice grants
                self.banner(["EXTRA ROLL!"], pos, (255, 150, 245), 1.2, 28)
                self.audio.play("double")
            m.res_bonus = []
            self.hint = "Roll the dice"
        else:
            self.set_state(S.NEXT_TURN)

    def do_end_turn(self):
        m = self.match
        prev = self.cur
        before = m.players[prev].shield_turns
        info = m.end_turn()
        if before > 0 and m.players[prev].shield_turns == 0:
            self.expired_until[prev] = self.t + 2.4
            z = L.zone_rect(prev)
            self.banner(["SHIELD EXPIRED"], (z.centerx, z.centery), CYAN, 1.6, 22)
        if info.skipped:
            self.skip_queue = list(info.skipped)
            self.start_skip()
        else:
            self.begin_turn_ui()

    # ----------------------------------------------------------------- bombs
    def start_bomb_if_due(self) -> bool:
        """At the end of a turn: has the hidden game-progress timer reached the next bomb?"""
        m = self.match
        if not SETTINGS.bombs or not m.bomb_due():
            return False
        self.bomb_cells = m.arm_bomb()
        self._warn_beeps = 0
        self.audio.play("bomb_warn")
        self.banner(["BOMB INCOMING!", f"BOMB {m.bombs.fired + 1} OF {m.bombs.total}  -  {len(self.bomb_cells)} SQUARES MARKED"],
                    (self.board_center()[0], BOARD_Y + 44), (255, 110, 90), 1.3, 32, 17)   # short, so the marked squares stay visible
        self.set_state(S.BOMB_WARNING)
        self.hint = ""
        return True

    def explode_bomb(self):
        res = self.match.detonate_bomb()
        self.audio.play("bomb")
        if SETTINGS.animations:
            self.shake.kick(11, .35)
        for idx in res.cells:
            c = ring_cell_rect(idx).center
            self.blasts.add(c)
            self.fx(c, (255, 160, 50), 22, speed=250)
            self.fx(c, (70, 70, 80), 12, speed=160, g=40)
        for tk in res.hit:
            fv = self.views[(tk.owner, tk.index)]
            self.return_anims.append(ReturnAnim(fv, token_px(tk.owner, STEP_YARD, tk.index), SETTINGS.dur(.9)))
            self.fx((fv.x, fv.y), self.color(tk.owner), 22, speed=230)
        for tk in res.saved:
            fv = self.views[(tk.owner, tk.index)]
            self.audio.play("shield_block")
            self.fx((fv.x, fv.y), CYAN, 24, speed=210, g=0)
            self.banner(["SHIELD BLOCKED THE BOMB!"], (fv.x, fv.y - 40), CYAN, 1.8, 22)
        n = len(res.hit)
        lines = [f"BOMB! {n} TOKEN{'S' if n != 1 else ''} SENT HOME"] if n else ["BOMB! NOBODY WAS HIT"]
        self.banner(lines, self.board_center(), (255, 150, 90), 2.0, 32)
        self.bomb_cells = []
        self.set_state(S.BOMB_EXPLOSION)

    def start_skip(self):
        self.skip_player = self.skip_queue.pop(0)
        self.audio.play("skip")
        z = L.zone_rect(self.skip_player)
        self.fx(z.center, (255, 170, 80), 28, speed=240)
        self.banner([self.label(self.skip_player), "TURN SKIPPED"], self.board_center(), (255, 190, 90), 1.5, 34, 28)
        self.set_state(S.TURN_SKIPPED)

    # ----------------------------------------------------------------- input
    def handle_event(self, e):
        if self.state == S.VICTORY and self.victory:
            self.victory.handle(e)
            return
        if self.menu_btn.handle(e):
            self.audio.play("click")
            self.on_exit("menu")
            return
        if e.type != pygame.MOUSEBUTTONDOWN or e.button != 1:
            return
        pos = e.pos
        if self.state == S.PLAYER_TURN:
            for seat, hand in self.hands.items():
                for cv in hand:
                    if cv.rect.collidepoint(pos):
                        if seat == self.cur and self.match.can_use_card(seat, cv.kind):
                            self.activate_card(cv)
                        else:
                            cv.deny = .3                  # not your card / locked
                        return
            if self.dice.hit(pos) and self.match.can_roll:
                self.start_roll()
        elif self.state == S.TOKEN_SELECTION:
            best, bd = None, 26      # generous radius so finger taps on a phone land
            for tk in self.selectable:
                v = self.views[(tk.owner, tk.index)]
                d = math.dist(pos, v.pos)
                if d < bd:
                    best, bd = tk, d
                cx, cy = L.chip_pos(tk.owner, tk.index)
                if math.dist(pos, (cx, cy)) < 14:        # also selectable from the player's token tray
                    best, bd = tk, 0
            if best:
                self.choose_token(best)
        elif self.state in (S.POWER_ANIMATION, S.DICE_ROLLING, S.TOKEN_MOVEMENT):
            # clicking a card mid-animation just gives a "denied" nudge
            for hand in self.hands.values():
                for cv in hand:
                    if cv.rect.collidepoint(pos):
                        cv.deny = .3

    # ---------------------------------------------------------------- update
    def update(self, dt):
        dt = min(dt, 1 / 20)
        self.t += dt
        self.state_t += dt
        self.mouse = pygame.mouse.get_pos()
        m = self.match
        self.menu_btn.update(dt, self.mouse)
        self.particles.update(dt)
        self.shake.update(dt)
        self.blasts.update(dt)
        for b in self.banners:
            b.update(dt)
        self.banners = [b for b in self.banners if not b.done]

        st = self.state
        if st == S.DETERMINING_FIRST_PLAYER:
            if self.state_t >= SETTINGS.dur(T_FIRST_TOTAL):
                m.start(self.first)
                self.begin_turn_ui()
        elif st == S.POWER_ANIMATION:
            fl = self.flight
            fl.update(dt)
            if fl.landed and not self.flight_landed:
                self.flight_landed = True
                info = CARD_INFO[fl.kind]
                c = fl.center
                self.fx(c, info.accent, 30, speed=260, g=60)
                kind_sound = {PowerType.SHIELD: "shield", PowerType.DOUBLE_DICE: "double", PowerType.SKIP: "skip"}[fl.kind]
                self.audio.play(kind_sound)
                if fl.kind == PowerType.SHIELD and SETTINGS.animations:
                    self.shake.kick(3, .2)
            if fl.done:
                self.flight = None
                self.set_state(S.PLAYER_TURN)
                self.hint = "Roll the dice"
        elif st == S.DICE_ROLLING:
            if self.rolling_dice.update(dt, self.mouse, False):
                self.after_roll()
        elif st == S.NO_MOVE:
            if self.state_t >= SETTINGS.dur(T_NO_MOVE):
                self.continue_or_end()
        elif st == S.TOKEN_SELECTION:
            if len({t.step for t in self.selectable}) == 1 and self.state_t >= SETTINGS.dur(T_AUTO_MOVE):
                self.choose_token(self.selectable[0])      # all candidates are equivalent: auto-play
        elif st == S.TOKEN_MOVEMENT:
            if self.move_anim and self.move_anim.update(dt):
                self.move_anim = None
                self.on_move_complete()
        elif st == S.CAPTURE_ANIMATION:
            for ra in list(self.return_anims):
                if ra.update(dt):
                    self.return_anims.remove(ra)
                    ra.view.cell_key = ra.view.logic_key()
            if self.state_t >= SETTINGS.dur(T_CAPTURE) and not self.return_anims:
                self.after_move()
        elif st == S.NEXT_TURN:
            if self.state_t >= SETTINGS.dur(T_NEXT):
                if not self.start_bomb_if_due():
                    self.do_end_turn()
        elif st == S.BOMB_WARNING:
            warn = SETTINGS.dur(T_BOMB_WARN)
            beeps = int(3 * self.state_t / warn)                  # a beep at 1/3 and 2/3 of the warning
            if beeps > self._warn_beeps and beeps < 3:
                self._warn_beeps = beeps
                self.audio.play("bomb_warn")
            if self.state_t >= warn:
                self.explode_bomb()
        elif st == S.BOMB_EXPLOSION:
            if self.state_t >= SETTINGS.dur(T_BOMB_BLAST) and not self.return_anims:
                self.do_end_turn()
        elif st == S.TURN_SKIPPED:
            if self.state_t >= SETTINGS.dur(T_SKIP):
                if self.skip_queue:
                    self.start_skip()
                else:
                    self.skip_player = None
                    self.begin_turn_ui()
        elif st == S.VICTORY and self.victory:
            self.victory.update(dt)
            if SETTINGS.animations:
                self.particles.confetti(WIDTH, 5)

        # a stray return animation must always finish, whatever the state
        if st != S.CAPTURE_ANIMATION:
            for ra in list(self.return_anims):
                if ra.update(dt):
                    self.return_anims.remove(ra)
                    ra.view.cell_key = ra.view.logic_key()

        # --- dice / cards / tokens visuals
        for seat, d in self.dices.items():
            if st == S.DICE_ROLLING and d is self.rolling_dice:
                continue                                   # already updated above
            d.update(dt, self.mouse, st == S.PLAYER_TURN and m.can_roll and seat == self.cur)
        self.update_cards(dt)
        self.update_tokens(dt)
        for p in m.players:
            self.shield_vis[p.index] = approach(self.shield_vis[p.index], 1.0 if p.shielded else 0.0, 4, dt)

    def card_mode(self, seat):
        if seat == self.focus and self.state != S.TURN_SKIPPED:
            m = self.match
            ok = self.state == S.PLAYER_TURN and m.turn.rolls_taken == 0 and m.turn.cards_used < MAX_CARDS_PER_TURN
            return "active" if ok else "locked"
        return "dim"

    def update_cards(self, dt):
        for seat, hand in self.hands.items():
            n = len(hand)
            mode = self.card_mode(seat)
            for i, cv in enumerate(hand):
                cv.set_target(L.card_slot(seat, i, n))          # remaining cards slide to re-centre
                cv.update(dt, self.mouse, mode == "active")

    def update_tokens(self, dt):
        groups = defaultdict(list)
        for v in self.views.values():
            if not v.moving:
                groups[v.cell_key].append(v)
        for key, vs in groups.items():
            offs = stack_offsets(len(vs)) if key[0] in ("ring", "lane") else [(0, 0)] * len(vs)
            for v, (ox, oy) in zip(vs, offs):
                v.ox, v.oy = approach(v.ox, ox, 14, dt), approach(v.oy, oy, 14, dt)
                v.scale = approach(v.scale, 0.82 if len(vs) > 1 and key[0] in ("ring", "lane") else 1.0, 14, dt)
        for v in self.views.values():
            if v.moving:
                v.ox, v.oy = approach(v.ox, 0, 20, dt), approach(v.oy, 0, 20, dt)
                v.scale = approach(v.scale, 1.12, 12, dt)

    # ------------------------------------------------------------------ draw
    def draw(self, surf):
        surf.blit(get_background(), (0, 0))
        sx, sy = self.shake.offset
        for seat in self.order:
            self.draw_zone(surf, seat)
        # board (shaken a little on captures); only the chosen colours are lit up
        surf.blit(board_surface(self.order), (BOARD_X - MARGIN + sx, BOARD_Y - MARGIN + sy))
        self.draw_yard_names(surf, sx, sy)
        if self.state == S.BOMB_WARNING:
            draw_danger_cells(surf, self.bomb_cells, self.t, min(1.0, self.state_t / SETTINGS.dur(T_BOMB_WARN)), sx, sy)
        self.draw_tokens(surf, sx, sy)
        if self.state == S.BOMB_WARNING:
            draw_danger_icons(surf, self.bomb_cells, self.t, sx, sy)
        self.blasts.draw(surf)
        self.draw_hud(surf)
        self.menu_btn.draw(surf)
        for seat, d in self.dices.items():
            d.draw(surf, self.state == S.PLAYER_TURN and self.match.can_roll and seat == self.cur, self.t, self.color(seat))
        self.draw_cards(surf)
        self.particles.draw(surf)
        if self.flight:
            self.flight.draw(surf)
        for b in self.banners:
            b.draw(surf)
        if self.state == S.DETERMINING_FIRST_PLAYER:
            self.draw_first_player(surf)
        if self.state == S.TURN_SKIPPED:
            self.draw_skip_overlay(surf)
        if self.state == S.VICTORY and self.victory:
            self.victory.draw(surf, self.t)
            self.particles.draw(surf)

    # --- board nameplates --------------------------------------------------
    def draw_yard_names(self, surf, sx=0, sy=0):
        """Each player's name on their own yard, in the top band above the four token sockets."""
        for p in self.match.players:
            ox, oy = YARD_ORIGIN[p.index]
            cx = BOARD_X + (ox + 3) * CELL + sx
            cy = BOARD_Y + oy * CELL + 29 + sy
            draw_text_fit(surf, p.label, 14, shade(self.color(p.index), .5), (cx, cy), 4 * CELL, min_size=9)

    # --- zones -------------------------------------------------------------
    def draw_zone(self, surf, seat):
        z = L.zone_rect(seat)
        p = self.match.players[seat]
        col = self.color(seat)
        active = seat == self.focus
        panel = pygame.Surface(z.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (14, 16, 40, 205 if active else 150), panel.get_rect(), border_radius=18)
        pygame.draw.rect(panel, (*col, 40 if active else 18), panel.get_rect().inflate(-6, -6), border_radius=15)
        surf.blit(panel, z.topleft)
        if active:
            draw_glow(surf, z.center, int(z.w * .72), col, .22 + .08 * math.sin(self.t * 3))
        pygame.draw.rect(surf, col if active else shade(col, .55), z, 3 if active else 2, border_radius=18)
        # header: the player's (custom) name gets the whole width; long names shrink, then get "..."
        nx, ny = L.name_pos(seat)
        draw_text_fit(surf, p.label, 17, lerp_color(col, WHITE, .35) if active else (150, 156, 190), (nx, ny),
                      L.NAME_MAX_W, shadow=(0, 0, 0), min_size=11)
        self.draw_zone_tags(surf, seat, z, active, col)
        # token tray: shows where each of the 4 tokens is
        for i, tk in enumerate(p.tokens):
            cx, cy = L.chip_pos(seat, i)
            self.draw_chip(surf, tk, cx, cy, col)

    def draw_zone_tags(self, surf, seat, z, active, col):
        """Compact status tags in the free slots left/right of the token row (so names never collide):
        left = shield counter / EXPIRED, right = YOUR TURN or a queued SKIP."""
        p = self.match.players[seat]
        y = z.y + L.TOKEN_DY
        left = pygame.Rect(z.x + 6, y - 10, 46, 20)
        right = pygame.Rect(z.right - 52, y - 10, 46, 20)
        if p.shield_turns > 0:
            pygame.draw.rect(surf, (20, 44, 90), left, border_radius=10)
            pygame.draw.rect(surf, CYAN, left, 2, border_radius=10)
            draw_card_icon(surf, PowerType.SHIELD, left.x + 12, left.centery, 6, CYAN)
            draw_text(surf, str(p.shield_turns), 14, CYAN, (left.x + 30, left.centery))
        elif self.expired_until.get(seat, 0) > self.t:
            a = clamp((self.expired_until[seat] - self.t) / .6) * 255
            draw_text_fit(surf, "EXPIRED", 10, (170, 190, 220), left.center, left.w, alpha=a, min_size=8)
        if active and self.state != S.DETERMINING_FIRST_PLAYER:
            draw_text(surf, "YOUR", 10, col, (right.centerx, right.centery - 6))          # stacked: fits the slot
            draw_text(surf, "TURN", 10, col, (right.centerx, right.centery + 6))
        elif seat in self.match.turn.skip_flags:           # a Skip card is waiting to skip this player
            pygame.draw.rect(surf, (70, 40, 14), right, border_radius=10)
            pygame.draw.rect(surf, (255, 180, 90), right, 2, border_radius=10)
            draw_card_icon(surf, PowerType.SKIP, right.x + 12, right.centery, 6, (255, 200, 110))
            draw_text(surf, "SKIP", 11, (255, 200, 110), (right.x + 22, right.centery), "midleft")

    def draw_chip(self, surf, tk, cx, cy, col):
        sel = self.state == S.TOKEN_SELECTION and tk in self.selectable
        r = 9
        if tk.finished:
            pygame.draw.circle(surf, (40, 34, 70), (cx, cy), r + 2)
            surf.blit(crown_surface(18), crown_surface(18).get_rect(center=(cx, cy)))
        elif tk.in_yard:
            surf.blit(token_sprite(col, r), token_sprite(col, r).get_rect(center=(cx, cy)))
        else:                                              # out on the board: ghost chip + progress ring
            pygame.draw.circle(surf, shade(col, .35), (cx, cy), r)
            pygame.draw.circle(surf, shade(col, .6), (cx, cy), r, 1)
            ang = tk.step / STEP_FINISH * 2 * math.pi
            rect = pygame.Rect(cx - r - 2, cy - r - 2, 2 * r + 4, 2 * r + 4)
            pygame.draw.arc(surf, col, rect, math.pi / 2, math.pi / 2 + ang, 3)
        if sel:
            draw_glow(surf, (cx, cy), 20, GOLD_LIGHT, .5 + .3 * math.sin(self.t * 8))
            pygame.draw.circle(surf, GOLD_LIGHT, (cx, cy), r + 4, 2)
        if self.shield_vis[tk.owner] > .02:
            pygame.draw.circle(surf, lerp_color(shade(col, .4), CYAN, self.shield_vis[tk.owner]), (cx, cy), r + 3, 1)

    # --- cards ---------------------------------------------------------------
    def draw_cards(self, surf):
        for seat in self.order:
            mode = self.card_mode(seat)
            col = self.color(seat)
            # draw hovered card last so it overlaps its neighbours
            for cv in sorted(self.hands[seat], key=lambda c: c.hover):
                cv.draw(surf, mode, self.t, col)

    # --- tokens --------------------------------------------------------------
    def draw_tokens(self, surf, sx, sy):
        order = sorted(self.views.values(), key=lambda v: (v.moving, v.y))
        hov = None
        if self.state == S.TOKEN_SELECTION:
            for tk in self.selectable:
                v = self.views[(tk.owner, tk.index)]
                if math.dist(self.mouse, v.pos) < 18:
                    hov = tk
            if hov is not None:                              # preview where the hovered token would land
                dest = target_step(hov, self.match.last_roll)
                if dest is not None:
                    px, py = token_px(hov.owner, dest, hov.index)
                    rr = 15 + 2 * math.sin(self.t * 8)
                    pygame.draw.circle(surf, GOLD_LIGHT, (px, py), int(rr), 2)
                    draw_glow(surf, (px, py), 22, GOLD_LIGHT, .35)
        for v in order:
            tk = v.token
            col = self.color(tk.owner)
            x, y = v.pos
            x, y = x + sx, y + sy
            if self.shield_vis[tk.owner] > .02:
                self.draw_shield_aura(surf, x, y, col, self.shield_vis[tk.owner], tk.index)
            sel = self.state == S.TOKEN_SELECTION and tk in self.selectable
            sc = v.scale * (1 + (.12 + .05 * math.sin(self.t * 9)) * sel)
            if sel:
                draw_glow(surf, (x, y), 26, GOLD_LIGHT, .55 + .25 * math.sin(self.t * 9))
            spr = token_sprite(col, TOKEN_R)
            if v.hop > 0:                                     # ground shadow while hopping
                sh = pygame.Surface((22, 10), pygame.SRCALPHA)
                pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
                surf.blit(sh, (x - 11, y + v.hop + 4))
            if abs(sc - 1) > .015:
                spr = pygame.transform.smoothscale(spr, (max(4, int(spr.get_width() * sc)), max(4, int(spr.get_height() * sc))))
            surf.blit(spr, spr.get_rect(center=(x, y)))
            if sel:
                pygame.draw.circle(surf, GOLD_LIGHT, (x, y - 1), int(TOKEN_R * sc) + 3, 2)

    def draw_shield_aura(self, surf, x, y, col, vis, idx):
        pulse = .5 + .5 * math.sin(self.t * 3 + idx)
        draw_glow(surf, (x, y), 24, CYAN, (.35 + .15 * pulse) * vis)
        r = TOKEN_R + 5 + pulse * 1.5
        ring = pygame.Surface((int(r * 2 + 6), int(r * 2 + 6)), pygame.SRCALPHA)
        c = ring.get_width() // 2
        pygame.draw.circle(ring, (*CYAN, int(190 * vis)), (c, c), int(r), 2)
        for k in range(3):                                    # orbiting sparkles
            a = self.t * 2.6 + k * 2.094 + idx
            pygame.draw.circle(ring, (255, 255, 255, int(230 * vis)), (c + math.cos(a) * r, c + math.sin(a) * r), 2)
        surf.blit(ring, ring.get_rect(center=(x, y)))

    # --- HUD -----------------------------------------------------------------
    def draw_hud(self, surf):
        r = L.HUD_RECT
        c = self.cur
        col = self.color(c) if self.state != S.DETERMINING_FIRST_PLAYER else GOLD
        panel = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (14, 16, 40, 200), panel.get_rect(), border_radius=20)
        surf.blit(panel, r.topleft)
        pygame.draw.rect(surf, shade(col, .8), r, 3, border_radius=20)
        wide = r.w > r.h * 2                         # phone layout: a wide strip, info side by side
        tx = r.x + int(r.w * .36) if wide else r.centerx
        if self.state == S.DETERMINING_FIRST_PLAYER:
            draw_text(surf, "GET READY", 26, GOLD_LIGHT, (tx, r.y + 30), shadow=(0, 0, 0))
        else:
            who = self.focus if self.focus is not None else c
            word = "SKIPPED" if self.state == S.TURN_SKIPPED else "TURN"
            draw_text_fit(surf, f"{self.label(who)} {word}", 28, self.color(who), (tx, r.y + 30),
                          (int(r.w * .6) if wide else r.w) - 28, shadow=(0, 0, 0), min_size=14)
        draw_text(surf, f"TURN {max(1, self.match.turn.turn_number)}", 12, (150, 158, 195), (tx, r.y + 56))
        if SETTINGS.bombs and self.state != S.DETERMINING_FIRST_PLAYER:
            b = self.match.bombs
            warn = self.state == S.BOMB_WARNING
            col = (255, 120, 100) if warn else (150, 158, 195)
            tr = draw_text(surf, f"BOMBS {b.fired}/{b.total}", 11, col, (tx + 8, r.y + 72))
            draw_bomb_icon(surf, tr.x - 11, tr.centery, 5, self.t)
        # roll info
        t = self.match.turn
        if wide:
            ix, ry, num_y, badge_y = r.right - 96, r.y + 24, r.y + 58, r.y + 92
        else:
            ix, ry, num_y, badge_y = r.centerx, r.y + 104, r.y + 140, r.y + 182
        if self.state != S.DETERMINING_FIRST_PLAYER:
            draw_text(surf, "ROLLS LEFT", 13, (150, 158, 195), (ix, ry))
            draw_text(surf, str(t.rolls_remaining), 44, WHITE, (ix, num_y), shadow=(0, 0, 0))
            if t.double_active:
                pulse = .75 + .25 * math.sin(self.t * 5)
                badge = pygame.Rect(0, 0, 110, 22 if wide else 26)
                badge.center = (ix, badge_y)
                pygame.draw.rect(surf, (88, 36, 140), badge, border_radius=13)
                pygame.draw.rect(surf, lerp_color((255, 140, 240), (255, 255, 255), 1 - pulse), badge, 2, border_radius=13)
                draw_text(surf, "DOUBLE DICE x2", 12, (255, 190, 250), badge.center)
        if self.hint:
            hx, hy = (tx, r.bottom - 22) if wide else (r.centerx, r.bottom - 18)
            draw_text(surf, self.hint, 15, GOLD_LIGHT, (hx, hy), alpha=200 + 55 * math.sin(self.t * 4))

    # --- overlays --------------------------------------------------------------
    def draw_first_player(self, surf):
        T = SETTINGS.dur(T_FIRST_CYCLE)
        order, n = self.order, self.n
        fi = order.index(self.first)
        cx, cy = self.board_center()
        veil = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(veil, (6, 8, 24, 228), veil.get_rect(), border_radius=16)
        surf.blit(veil, (BOARD_X, BOARD_Y))
        if self.state_t < T:
            p = ease_in_out(self.state_t / T) ** .7
            total = n * 3 + fi
            hi = order[int(p * total) % n if self.state_t < T - .05 else fi]
            draw_text(surf, "DETERMINING", 30, GOLD_LIGHT, (cx, cy - 70), shadow=(0, 0, 0))
            draw_text(surf, "FIRST PLAYER...", 30, GOLD_LIGHT, (cx, cy - 36), shadow=(0, 0, 0))
            for k, c in enumerate(order):
                x = cx + (k - (n - 1) / 2) * 76
                col = self.color(c)
                on = c == hi
                if on:
                    draw_glow(surf, (x, cy + 30), 52, col, .7)
                pygame.draw.circle(surf, col if on else shade(col, .35), (x, cy + 30), 26 if on else 20)
                pygame.draw.circle(surf, WHITE if on else shade(col, .6), (x, cy + 30), 26 if on else 20, 3)
                draw_text(surf, short_tag(self.match.players[c].name), 16, WHITE if on else (150, 150, 170), (x, cy + 30))
                draw_text_fit(surf, self.label(c), 12, WHITE if on else (130, 134, 160), (x, cy + 68), 72, min_size=8)
            hz = L.zone_rect(hi)
            pygame.draw.rect(surf, self.color(hi), hz, 4, border_radius=18)
        else:
            k = clamp((self.state_t - T) / .35)
            col = self.color(self.first)
            draw_glow(surf, (cx, cy), 200, col, .5 * k)
            draw_text_fit(surf, self.label(self.first), int(50 * ease_out_back(k)) + 1, col, (cx, cy - 20), BOARD_SIZE - 40,
                          shadow=(0, 0, 0), min_size=14)
            draw_text(surf, "STARTS!", int(44 * ease_out_back(k)) + 1, WHITE, (cx, cy + 36), shadow=(0, 0, 0))
            pygame.draw.rect(surf, col, L.zone_rect(self.first), 4, border_radius=18)

    def draw_skip_overlay(self, surf):
        z = L.zone_rect(self.skip_player)
        k = clamp(self.state_t / SETTINGS.dur(T_SKIP))
        a = int(170 * min(1, k * 6) * min(1, (1 - k) * 4))
        ov = pygame.Surface(z.size, pygame.SRCALPHA)
        pygame.draw.rect(ov, (30, 14, 6, a), ov.get_rect(), border_radius=18)
        for i in range(-z.h, z.w, 26):                         # warning stripes
            pygame.draw.line(ov, (255, 170, 60, int(a * .45)), (i, z.h), (i + z.h, 0), 8)
        surf.blit(ov, z.topleft)
        draw_text(surf, "TURN SKIPPED", 22, (255, 200, 110), (z.centerx, z.centery), shadow=(0, 0, 0), alpha=255 * min(1, k * 6) * min(1, (1 - k) * 4))
        draw_card_icon(surf, PowerType.SKIP, z.centerx, z.centery - 34, 16, (255, 200, 110))
