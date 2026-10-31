from powers.power_card import PowerType, CARD_INFO, CARD_ORDER, PowerEffect
from powers.shield import ShieldEffect
from powers.double_dice import DoubleDiceEffect
from powers.skip import SkipEffect

EFFECTS: dict[PowerType, PowerEffect] = {
    PowerType.SHIELD: ShieldEffect(),
    PowerType.DOUBLE_DICE: DoubleDiceEffect(),
    PowerType.SKIP: SkipEffect(),
}
