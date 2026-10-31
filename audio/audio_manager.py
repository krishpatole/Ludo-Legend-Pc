"""AudioManager: loads files from assets/sounds if present, otherwise synthesises a
placeholder so the game always has sound. Never raises if audio is unavailable."""
from __future__ import annotations
import math, os, random, struct
from array import array
import pygame
from config.settings import SETTINGS

from utils.helpers import resource_path
SND_DIR = resource_path("assets", "sounds")
RATE = 22050
EXTS = (".ogg", ".wav", ".mp3")
NAMES = ("click", "dice", "move", "capture", "shield", "shield_block", "skip", "double",
         "bonus", "home", "victory", "card", "bomb_warn", "bomb")


def _tone(freq, dur, vol=0.5, decay=6.0, f_end=None, noise=0.0, wave="sine"):
    n = int(RATE * dur)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / n
        f = freq + ((f_end - freq) * t if f_end else 0)
        ph += 2 * math.pi * f / RATE
        s = math.sin(ph) if wave == "sine" else (1.0 if math.sin(ph) > 0 else -1.0) * 0.6
        s += (random.random() * 2 - 1) * noise
        out.append(s * vol * math.exp(-decay * t) * min(1.0, i / 80))
    return out


def _mix(*parts):
    n = max(len(p[1]) + p[0] for p in parts)
    buf = [0.0] * n
    for off, samples in parts:
        for i, v in enumerate(samples):
            buf[off + i] += v
    return buf


def _seq(notes, gap=0.08, **kw):
    return _mix(*[(int(RATE * gap * i), _tone(f, kw.get("dur", 0.18), kw.get("vol", .4), kw.get("decay", 5)))
                  for i, f in enumerate(notes)])


def _synth(name):
    if name == "click":   return _tone(900, .07, .35, 20)
    if name == "card":    return _tone(500, .12, .35, 9, 900)
    if name == "move":    return _tone(520, .06, .3, 18)
    if name == "dice":    return _mix(*[(int(RATE * .045 * i), _tone(random.randint(300, 700), .04, .35, 12, noise=.5)) for i in range(11)])
    if name == "bomb_warn": return _seq((960, 960, 960), .2, dur=.14, vol=.4, decay=9)
    if name == "bomb":    return _mix((0, _tone(70, .9, .9, 3.2, 28, noise=.55)), (0, _tone(240, .35, .5, 9, noise=1.0)), (0, _tone(1400, .12, .3, 25, noise=.9)))
    if name == "capture": return _mix((0, _tone(620, .38, .5, 5, 120)), (0, _tone(200, .3, .4, 8, noise=.8)))
    if name == "shield":  return _seq((440, 660, 880, 1320), .07, dur=.35, vol=.3, decay=4)
    if name == "shield_block": return _mix((0, _tone(1250, .3, .4, 7)), (0, _tone(1870, .25, .3, 9)), (0, _tone(300, .1, .4, 14, noise=.4)))
    if name == "skip":    return _seq((700, 520, 340), .11, dur=.18, vol=.4, decay=6)
    if name == "double":  return _seq((520, 780, 1040), .06, dur=.2, vol=.35, decay=6)
    if name == "bonus":   return _seq((880, 1320), .08, dur=.25, vol=.4, decay=6)
    if name == "home":    return _seq((523, 659, 784), .09, dur=.3, vol=.35, decay=4)
    if name == "victory": return _seq((523, 659, 784, 1047, 784, 1047, 1318), .13, dur=.45, vol=.35, decay=3)
    return _tone(440, .1)


def _to_sound(samples, gain=1.0):
    buf = array("h", (int(max(-1, min(1, s * gain)) * 32000) for s in samples))
    return pygame.mixer.Sound(buffer=buf.tobytes())


class AudioManager:
    def __init__(self):
        self.ok = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music_ch = None
        self._music_snd = None
        self._music_file = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=512)
            pygame.mixer.set_num_channels(16)
            self.ok = True
        except Exception as e:                       # no audio device: run silently
            print("[audio] disabled:", e)
            return
        random.seed(7)
        for n in NAMES:
            self.sounds[n] = self._load(n)
        random.seed()

    def _load(self, name):
        for ext in EXTS:
            p = os.path.join(SND_DIR, name + ext)
            if os.path.isfile(p):
                try:
                    return pygame.mixer.Sound(p)
                except Exception as e:
                    print(f"[audio] bad file {p}: {e}")
        try:
            return _to_sound(_synth(name))
        except Exception:
            return None

    def play(self, name: str, vol: float = 1.0) -> None:
        if not (self.ok and SETTINGS.sfx):
            return
        s = self.sounds.get(name)
        if s:
            s.set_volume(vol)
            s.play()

    # ---- music -----------------------------------------------------------
    def _build_music(self):
        for ext in EXTS:
            p = os.path.join(SND_DIR, "music" + ext)
            if os.path.isfile(p):
                try:
                    return pygame.mixer.Sound(p)
                except Exception:
                    pass
        chords = ((220, 261.6, 329.6), (174.6, 220, 261.6), (196, 246.9, 293.7), (164.8, 207.7, 246.9))
        beat = 0.3
        samples = []
        for ch in chords:
            for i in range(8):
                f = ch[(0, 1, 2, 1, 0, 1, 2, 1)[i]] * 2
                samples += _tone(f, beat, .22, 3.2) + [0.0] * 0
        bass = []
        for ch in chords:
            bass += _tone(ch[0] / 2, beat * 8, .22, .6)
        n = min(len(samples), len(bass))
        return _to_sound([samples[i] + bass[i] for i in range(n)], 0.7)

    def start_music(self):
        if not (self.ok and SETTINGS.music):
            return
        try:
            if self._music_snd is None:
                self._music_snd = self._build_music()
            if self.music_ch is None or not self.music_ch.get_busy():
                self._music_snd.set_volume(0.22)
                self.music_ch = self._music_snd.play(loops=-1)
        except Exception as e:
            print("[audio] music failed:", e)

    def stop_music(self):
        if self.ok and self.music_ch:
            self.music_ch.stop()
            self.music_ch = None

    def apply_settings(self):
        self.start_music() if SETTINGS.music else self.stop_music()


AUDIO: AudioManager | None = None


def get_audio() -> AudioManager:
    global AUDIO
    if AUDIO is None:
        AUDIO = AudioManager()
    return AUDIO
