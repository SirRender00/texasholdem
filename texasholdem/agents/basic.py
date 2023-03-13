"""
Basic agents are included in this module:
    - :func:`call_agent`
    - :func:`random_agent`

"""

from typing import Tuple

import random

from texasholdem.game.game import TexasHoldEm
from texasholdem.game.action_type import ActionType
from texasholdem.game.player_state import PlayerState


def call_agent(game: TexasHoldEm) -> Tuple[ActionType, None]:
    """
    A player that calls if another player raised or checks.

    Arguments:
        game (TexasHoldEm): The TexasHoldEm game
    Returns:
        Tuple[ActionType, None]: CALL if someone raised, else CHECK

    """
    player = game.players[game.current_player]
    if player.state == PlayerState.TO_CALL:
        return ActionType.CALL, None
    return ActionType.CHECK, None


def random_agent(game: TexasHoldEm, no_fold: bool = False) -> Tuple[ActionType, int]:
    """
    A uniformly random player

        - If someone raised, CALL, FOLD, or RAISE with uniform probability
        - Else, CHECK, (FOLD if no_fold=False), RAISE with uniform probability
        - If RAISE, the value will be uniformly random in [min_raise, # of chips]

    Arguments:
        game (TexasHoldEm): The TexasHoldEm game
        no_fold (bool): Removes the possibility of folding if no one raised, default False.
    Returns:
        Tuple[ActionType, int]: Returns a uniformly random action from the
            available moves.

    """
    moves = game.get_available_moves()
    if no_fold:
        del moves[ActionType.FOLD]

    return moves.sample()
