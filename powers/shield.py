from config.settings import SHIELD_TURNS
from powers.power_card import PowerEffect, PowerType


class ShieldEffect(PowerEffect):
    kind = PowerType.SHIELD

    def activate(self, match, player):
        player.shield_turns = SHIELD_TURNS
        match.turn.shield_started_this_turn = True    # activation turn is not counted
        return ("SHIELD", f"{player.label} ACTIVATED", f"{SHIELD_TURNS} TURNS PROTECTED")
