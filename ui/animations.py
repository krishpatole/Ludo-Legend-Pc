"""Reusable animation utilities: tweens, particles, banners, screen shake."""
from __future__ import annotations
import math, random
import pygame
from utils.helpers import ease_out_cubic, clamp, draw_text, draw_text_fit, draw_glow, lerp


class Tween:
    """Value animation a -> b over ``duration`` using an easing function."""

    def __init__(self, a, b, duration, ease=ease_out_cubic):
        self.a, self.b, self.d, self.ease, self.t = a, b, max(1e-4, duration), ease, 0.0

    def update(self, dt):
        self.t = min(self.d, self.t + dt)
        return self.value

    @property
    def value(self):
        return lerp(self.a, self.b, self.ease(self.t / self.d))

    @property
    def done(self):
        return self.t >= self.d


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "size", "g", "shape", "rot", "vr")

    def __init__(self, x, y, vx, vy, life, color, size, g=0.0, shape="circle"):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color, self.size, self.g, self.shape = color, size, g, shape
        self.rot, self.vr = random.random() * 6.28, random.uniform(-8, 8)


class ParticleSystem:
    def __init__(self, limit=700):
        self.p: list[Particle] = []
        self.limit = limit

    def burst(self, pos, color, n=18, speed=170, life=0.7, size=4, g=260):
        for _ in range(n):
            a, s = random.random() * 6.283, random.uniform(.3, 1) * speed
            if len(self.p) < self.limit:
                self.p.append(Particle(pos[0], pos[1], math.cos(a) * s, math.sin(a) * s,
                                       life * random.uniform(.6, 1.1), color, size * random.uniform(.6, 1.2), g))

    def sparkle_ring(self, pos, color, radius, n=10):
        for _ in range(n):
            a = random.random() * 6.283
            if len(self.p) < self.limit:
                self.p.append(Particle(pos[0] + math.cos(a) * radius, pos[1] + math.sin(a) * radius,
                                       math.cos(a) * 20, math.sin(a) * 20 - 25, .6, color, 2.5, 0))

    def confetti(self, width, n=6, colors=((222, 66, 66), (52, 178, 96), (62, 118, 226), (244, 194, 44), (255, 255, 255))):
        for _ in range(n):
            if len(self.p) < self.limit:
                self.p.append(Particle(random.uniform(0, width), -12, random.uniform(-40, 40), random.uniform(60, 200),
                                       random.uniform(3.5, 6), random.choice(colors), random.uniform(5, 9), 40, "rect"))

    def update(self, dt):
        for q in self.p:
            q.life -= dt
            q.vy += q.g * dt
            q.x += q.vx * dt
            q.y += q.vy * dt
            q.rot += q.vr * dt
        self.p = [q for q in self.p if q.life > 0]

    def draw(self, surf):
        for q in self.p:
            a = clamp(q.life / q.max)
            if q.shape == "rect":
                w, h = q.size, q.size * .55 * (abs(math.cos(q.rot)) + .2)
                r = pygame.Rect(0, 0, w, h)
                r.center = (q.x, q.y)
                pygame.draw.rect(surf, q.color, r)
            else:
                s = max(1, q.size * (.4 + .6 * a))
                if a > .35:
                    draw_glow(surf, (q.x, q.y), int(s * 2.6), q.color, .5)
                pygame.draw.circle(surf, q.color, (int(q.x), int(q.y)), int(s))


class Banner:
    """Short-lived popup text that scales in, holds, fades out."""

    def __init__(self, lines, pos, color, duration=1.6, size=30, sub_size=18):
        self.lines, self.pos, self.color, self.dur, self.t = lines, pos, color, duration, 0.0
        self.size, self.sub = size, sub_size

    @property
    def done(self):
        return self.t >= self.dur

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        k = self.t / self.dur
        a = 255 * (min(1, k * 8) * min(1, (1 - k) * 5))
        s = 0.6 + 0.4 * min(1, k * 7) + 0.04 * k
        y = self.pos[1] - 14 * k
        for i, line in enumerate(self.lines):
            sz = int((self.size if i == 0 else self.sub) * s)
            col = self.color if i == 0 else (240, 240, 255)
            draw_text_fit(surf, line, max(8, sz), col, (self.pos[0], y + i * self.size * .95), 430, shadow=(0, 0, 0), alpha=a, min_size=9)


class Shake:
    def __init__(self):
        self.t = 0.0
        self.mag = 0.0

    def kick(self, mag=6, t=.25):
        self.mag, self.t = mag, t

    def update(self, dt):
        self.t = max(0, self.t - dt)

    @property
    def offset(self):
        if self.t <= 0:
            return 0, 0
        m = self.mag * self.t / .25
        return random.uniform(-m, m), random.uniform(-m, m)
