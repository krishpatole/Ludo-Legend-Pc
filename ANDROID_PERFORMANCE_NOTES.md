# Android performance changes

This update keeps game rules, visuals, animations, and desktop behaviour intact while reducing avoidable work in the Android presentation loop.

- Android uses pygame's faster `transform.scale` for the final full-screen presentation; desktop retains `smoothscale`.
- The fade overlay Surface is created once and reused instead of allocated on every frame.
- Android and desktop target 60 FPS. This is a maximum frame-rate cap, not a guarantee; sustained FPS depends on device, thermal state, rendering load, and display refresh rate.

The actual improvement must be measured on the target phone. If the game still stutters, profile scene drawing and animated sprite generation next; do not assume these changes alone resolve every device-specific bottleneck.
