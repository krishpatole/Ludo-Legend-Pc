"""All screen-layout maths in one place so nothing overlaps.

Seats (clockwise): 0 Red = left, 1 Green = top, 2 Blue = right, 3 Yellow = bottom.
Every zone is stacked:  NAME  ->  4 TOKENS  ->  3 POWER CARDS.
"""
from __future__ import annotations
import pygame
from config.settings import (PORTRAIT, WIDTH, HEIGHT, BOARD_X, BOARD_Y, BOARD_SIZE, ZONE_W, ZONE_H,
                             CARD_W, CARD_H, CARD_GAP)

NAME_DY, TOKEN_DY, CARD_TOP_DY = 14, 38, 52
NAME_MAX_W = ZONE_W - 24          # widest a player name may be drawn in the zone header
_gap = 34


# Portrait (phone): HUD strip on top, Red/Green zones above the board, Yellow/Blue zones below it.
P_TOP_Y = 152
P_BOT_Y = BOARD_Y + BOARD_SIZE + 16


def zone_rect(seat: int) -> pygame.Rect:
    if PORTRAIT:
        x_l, x_r = 16, WIDTH - 16 - ZONE_W
        return {0: pygame.Rect(x_l, P_TOP_Y, ZONE_W, ZONE_H), 1: pygame.Rect(x_r, P_TOP_Y, ZONE_W, ZONE_H),
                3: pygame.Rect(x_l, P_BOT_Y, ZONE_W, ZONE_H), 2: pygame.Rect(x_r, P_BOT_Y, ZONE_W, ZONE_H)}[seat]
    cx = BOARD_X + BOARD_SIZE // 2
    mid_y = BOARD_Y + (BOARD_SIZE - ZONE_H) // 2          # side zones are centred on the board
    if seat == 0:   # left
        return pygame.Rect(BOARD_X - _gap - ZONE_W, mid_y, ZONE_W, ZONE_H)
    if seat == 1:   # top centre
        return pygame.Rect(cx - ZONE_W // 2, 4, ZONE_W, ZONE_H)
    if seat == 2:   # right
        return pygame.Rect(BOARD_X + BOARD_SIZE + _gap, mid_y, ZONE_W, ZONE_H)
    return pygame.Rect(cx - ZONE_W // 2, HEIGHT - 4 - ZONE_H, ZONE_W, ZONE_H)   # bottom centre


def name_pos(seat):
    z = zone_rect(seat)
    return z.centerx, z.y + NAME_DY


def chip_pos(seat, i):
    z = zone_rect(seat)
    return z.centerx + (i - 1.5) * 36, z.y + TOKEN_DY


def card_slot(seat, i, n):
    """Centre of the i-th of n cards in the player's hand (re-centres when a card is used)."""
    z = zone_rect(seat)
    return z.centerx + (i - (n - 1) / 2) * (CARD_W + CARD_GAP), z.y + CARD_TOP_DY + CARD_H / 2


# Turn panel top-right, MENU button top-left (mirrored corners). The old "coins home" status box is gone.
if PORTRAIT:
    HUD_RECT = pygame.Rect(16, 16, WIDTH - 32, 120)
    MENU_BTN = pygame.Rect(WIDTH // 2 - 90, P_BOT_Y + ZONE_H + 24, 180, 52)
else:
    HUD_RECT = pygame.Rect(BOARD_X + BOARD_SIZE + 40, 24, 330, 236)
    MENU_BTN = pygame.Rect(24, 24, 150, 46)


DICE_SIZE = 62


def dice_center(seat: int):
    """Each player owns a die beside their own zone (left/right of it, level with the cards)."""
    z = zone_rect(seat)
    if PORTRAIT:     # dice sit in the gap between the two zones of the same row
        return (z.right + 52 if seat in (0, 3) else z.x - 52), z.y + 78
    cy = z.y + (60 if seat in (1, 3) else CARD_TOP_DY + CARD_H // 2 - 6)
    if seat == 0:
        return z.x - 66, cy
    return z.right + 66, cy          # right of the zone for seats 1, 2, 3
