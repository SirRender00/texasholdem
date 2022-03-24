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
        tuple[ActionType, None]: CALL if someone raised, else CHECK

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
        tuple[ActionType, int]: Returns a uniformly random action from the
            available moves.

    """
    bet_amount = game.player_bet_amount(game.current_player)
    chips = game.players[game.current_player].chips
    min_raise = game.value_to_total(game.min_raise(), game.current_player)
    max_raise = bet_amount + chips

    possible = list(ActionType)
    possible.remove(ActionType.ALL_IN)

    # A player did not raise
    if game.players[game.current_player].state == PlayerState.IN:
        possible.remove(ActionType.CALL)
        if no_fold:
            possible.remove(ActionType.FOLD)

    # A player raised
    if game.players[game.current_player].state == PlayerState.TO_CALL:
        possible.remove(ActionType.CHECK)

    # not enough chips to raise
    if max_raise < min_raise:
        possible.remove(ActionType.RAISE)

    action_type, total = random.choice(possible), None
    if action_type == ActionType.RAISE:
        total = random.randint(min_raise, max_raise)

    return action_type, total
