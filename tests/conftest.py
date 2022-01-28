import pytest

from texasholdem.game.game import TexasHoldEm
from texasholdem.game.action_type import ActionType
from texasholdem.game.player_state import PlayerState


@pytest.fixture()
def call_player():

    def get_action(game: TexasHoldEm):
        player = game.players[game.current_player]
        if player.state == PlayerState.TO_CALL:
            return ActionType.CALL, None
        else:
            return ActionType.CHECK, None

    return get_action
