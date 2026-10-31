from powers.power_card import PowerEffect, PowerType


class DoubleDiceEffect(PowerEffect):
    kind = PowerType.DOUBLE_DICE

    def activate(self, match, player):
        match.turn.grant_double()
        return ("DOUBLE DICE", f"{player.label} ACTIVATED", "ONE EXTRA ROLL")
