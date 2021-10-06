"""The history module includes various dataclasses intended
to keep the history of the game to be able to replay hands and
save what happened. It includes a random_seed so that seeding
the python random module with it will run the hand exactly
as it occurred.
"""

from typing import Optional
from dataclasses import dataclass

from texasholdem.game.action_type import ActionType


@dataclass(frozen=True)
class PrehandHistory:
    """Prehand history class, includes random_seed, button location, and
    the player chip counts."""
    random_seed: object
    btn_loc: int
    player_chips: dict[int, int]


@dataclass(frozen=True)
class PlayerAction:
    """PlayerAction history class, includes the player id, the action type,
    and the value."""
    player_id: int
    action_type: ActionType
    value: Optional[int]


@dataclass(frozen=True)
class BettingRoundHistory:
    """BettingRound history class, includes a list of PlayerActions."""
    actions: list[PlayerAction]
