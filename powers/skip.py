from powers.power_card import PowerEffect, PowerType


class SkipEffect(PowerEffect):
    kind = PowerType.SKIP

    def activate(self, match, player):
        target = match.turn.mark_skip_next()
        return ("SKIP", f"{player.label} ACTIVATED", f"{match.players[target].label} WILL BE SKIPPED")
