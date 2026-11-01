# Android performance changes

This update keeps game rules, visuals, animations, and desktop behaviour intact while reducing avoidable work in the Android presentation loop.

- Android uses pygame's faster `transform.scale` for the final full-screen presentation; desktop retains `smoothscale`.
- The fade overlay Surface is created once and reused instead of allocated on every frame.
- Android and desktop target 60 FPS. This is a maximum frame-rate cap, not a guarantee; sustained FPS depends on device, thermal state, rendering load, and display refresh rate.

The actual improvement must be measured on the target phone. If the game still stutters, profile scene drawing and animated sprite generation next; do not assume these changes alone resolve every device-specific bottleneck.

## Round 2 - what was actually causing the freeze / jerk (measured with a profiler on a PC)

| Cause | Before (PC) | After (PC) |
|---|---|---|
| Sounds + music were synthesised in pure Python at start-up | 1366 ms (many seconds on a phone) | 6 ms - sounds are pre-rendered WAV files in `assets/sounds/` (regenerate with `python tools/make_sounds.py`) |
| Pressing START GAME built the board, cards, dice, glows and text for the first time | one 56-70 ms frame (about 220 ms measured cold) | 13-19 ms - everything is built behind a LOADING screen (`game/warmup.py`) |
| Glow sprites were rebuilt for every new strength level while pulsing | small hitches during play | one cached sprite per size/colour; strength = alpha |
| Card shadows, dim veils and zone panels re-drawn from scratch every frame | ~2.8 ms/frame | cached |
| Final scale made a temporary surface each frame and cleared the window every frame | extra copy | scales straight into the window; letter-box bars painted only when the size changes |
| After any stall `dt` became huge and animations jumped | - | `dt` capped at 1/20 s |

PC per-frame cost: 7.7 ms -> 6.3 ms (a phone is several times slower, so measure on the device).
Not verified on a phone: no device was available. If it is still slow, the next step is hardware scaling
(`pygame.SCALED`) which needs the touch-mapping code re-checked on a device.
