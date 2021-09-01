from typing import Optional
from dataclasses import dataclass

from texasholdem.game.action_type import ActionType


@dataclass(frozen=True)
class PrehandHistory:
    random_seed: object
    btn_loc: int
    player_chips: dict[int, int]


@dataclass(frozen=True)
class PlayerAction:
    player_id: int
    action_type: ActionType
    value: Optional[int]


@dataclass(frozen=True)
class BettingRoundHistory:
    actions: list[PlayerAction]
