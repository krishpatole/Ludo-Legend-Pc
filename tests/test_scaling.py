"""App-level scaling: a phone-sized window must still map taps to the right canvas spot."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_harness import *
from game.app import App
app = App()
app.window = pygame.display.set_mode((800, 480), pygame.RESIZABLE)          # smaller, different aspect (letter-boxed)
k, off, size = app._viewport()
assert size[0] <= 800 and size[1] <= 480 and abs(size[0] / size[1] - WIDTH / HEIGHT) < .01
cx, cy = app.to_canvas((off[0] + size[0] // 2, off[1] + size[1] // 2))
assert abs(cx - WIDTH // 2) <= 2 and abs(cy - HEIGHT // 2) <= 2, (cx, cy)
app.scene.update(1 / 60); app.scene.draw(app.screen); app.present()
app.window = pygame.display.set_mode((1920, 1080), pygame.RESIZABLE)       # big screen
assert abs(app._viewport()[2][0] - 1920) <= 1 and abs(app._viewport()[2][1] - 1080) <= 1
app.window = pygame.display.set_mode((480, 800), pygame.RESIZABLE)         # portrait phone -> still fits (letter-boxed)
assert app._viewport()[2][0] == 480
app.present()
# degenerate sizes must not crash (minimised window)
class _Fake:
    def get_size(self): return (0, 0)
real = app.window
app.window = _Fake(); app._viewport(); app.to_canvas((5, 5)); app.window = real
# a real VIDEORESIZE-style change followed by a frame keeps working and maps taps correctly
app.window = pygame.display.set_mode((1000, 700), pygame.RESIZABLE)
app.frame(1 / 60, [pygame.event.Event(pygame.VIDEORESIZE, size=(1000, 700), w=1000, h=700)])
k, off, size = app._viewport(); assert size[0] <= 1000 and size[1] <= 700
print("SCALING OK")
# creating several Apps in one process (and toggling fullscreen) must never shrink the window towards zero
sizes = []
for _ in range(6):
    a = App(); sizes.append(a.window.get_size()); assert min(sizes[-1]) >= 300, sizes
assert len(set(sizes)) == 1, sizes
a.toggle_fullscreen(); assert a.fullscreen and a._viewport()[0] > 0
a.toggle_fullscreen(); assert not a.fullscreen and a._viewport()[0] > 0
# (the dummy video driver ignores leaving fullscreen, so the restored size can only be checked on a real display)
print("WINDOW SIZE STABLE", sizes[0])
