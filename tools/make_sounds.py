"""Pre-render every game sound into assets/sounds/*.wav (run once on a PC:  python tools/make_sounds.py).

Why: synthesising 14 sounds + the music loop in pure Python takes ~1.5 s on a PC and many seconds on a phone, which
froze the app at start-up. The game loads these files when present and only falls back to synthesis if they are missing.
"""
import os, sys, wave, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from audio import audio_manager as A

OUT = os.path.join(ROOT, "assets", "sounds")
os.makedirs(OUT, exist_ok=True)


def save(name, samples, gain=1.0):
    pcm = bytearray()
    for s in samples:
        v = int(max(-1, min(1, s * gain)) * 32000)
        pcm += v.to_bytes(2, "little", signed=True)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(A.RATE); w.writeframes(bytes(pcm))
    print(f"{name}.wav  {len(pcm) / 1024:.0f} KB")


random.seed(7)
for n in A.NAMES:
    save(n, A._synth(n))
random.seed()
samples, bass = [], []
chords = ((220, 261.6, 329.6), (174.6, 220, 261.6), (196, 246.9, 293.7), (164.8, 207.7, 246.9))
for ch in chords:
    for i in range(8):
        samples += A._tone(ch[(0, 1, 2, 1, 0, 1, 2, 1)[i]] * 2, 0.3, .22, 3.2)
    bass += A._tone(ch[0] / 2, 0.3 * 8, .22, .6)
n = min(len(samples), len(bass))
save("music", [samples[i] + bass[i] for i in range(n)], 0.7)
