"""All screen-layout maths in one place so nothing overlaps.

Seats (clockwise): 0 Red = left, 1 Green = top, 2 Blue = right, 3 Yellow = bottom.
Every zone is stacked:  NAME  ->  4 TOKENS  ->  3 POWER CARDS.
"""
from __future__ import annotations
import pygame
from config.settings import (WIDTH, HEIGHT, BOARD_X, BOARD_Y, BOARD_SIZE, ZONE_W, ZONE_H,
                             CARD_W, CARD_H, CARD_GAP)

NAME_DY, TOKEN_DY, CARD_TOP_DY = 14, 38, 52
NAME_MAX_W = ZONE_W - 24          # widest a player name may be drawn in the zone header
_gap = 34


def zone_rect(seat: int) -> pygame.Rect:
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
HUD_RECT = pygame.Rect(BOARD_X + BOARD_SIZE + 40, 24, 330, 236)
MENU_BTN = pygame.Rect(24, 24, 150, 46)


DICE_SIZE = 62


def dice_center(seat: int):
    """Each player owns a die beside their own zone (left/right of it, level with the cards)."""
    z = zone_rect(seat)
    cy = z.y + (60 if seat in (1, 3) else CARD_TOP_DY + CARD_H // 2 - 6)
    if seat == 0:
        return z.x - 66, cy
    return z.right + 66, cy          # right of the zone for seats 1, 2, 3
