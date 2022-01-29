"""
Config for game tests. Includes:
    - History file with comments
    - Call player fixture
    - And a method containing assert checks for the prehand for a game
"""
from typing import Tuple

import pytest

from texasholdem.game.game import TexasHoldEm
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.action_type import ActionType
from texasholdem.game.player_state import PlayerState

from tests.conftest import GOOD_GAME_HISTORY_DIRECTORY


@pytest.fixture()
def history_file_with_comments():
    """
    Returns:
        str: A path to a valid history file with comments
    """
    return GOOD_GAME_HISTORY_DIRECTORY / "call_game_6.pgn"


@pytest.fixture()
def texas_game():
    """
    Returns:
        TexasHoldEm: A "standard" full-ring game of texas hold em (2/5 blinds 500 buyin 9 players)
    """
    return TexasHoldEm(buyin=500, big_blind=5, small_blind=2)


@pytest.fixture()
def call_player():
    """
    Returns:
        Callable[[TexasHoldEm], Tuple[ActionType, None]]:
            A call player strategy (call if there was a raise, o/w check)
    """

    def get_action(game: TexasHoldEm) -> Tuple[ActionType, None]:
        player = game.players[game.current_player]
        if player.state == PlayerState.TO_CALL:
            return ActionType.CALL, None
        return ActionType.CHECK, None

    return get_action


def prehand_checks(texas: TexasHoldEm):
    """
    Tests basic state after running prehand:
        - hand_phase state should be PREFLOP
        - game_state should be RUNNING
        - Blinds should be posted
        - Blind locations should be sequential
        - Players should have TO_CALL status, (big blind player should have IN status)
        - Current player should be left of Big blind
        - Players should have 2 cards
        - The Board should not have any cards

    """
    # pylint: disable=protected-access
    assert texas.hand_phase == HandPhase.PREHAND

    # Gather pre-info to check differences / info that will be overwritten
    player_chips = [texas.players[i].chips for i in range(texas.max_players)]
    active_players = [i for i in range(texas.max_players)
                      if player_chips[i] > 0]
    starting_pot = texas.starting_pot

    # RUN PREHAND
    texas.start_hand()

    # state info
    sb_posted = min(texas.small_blind, player_chips[texas.sb_loc])
    bb_posted = min(texas.big_blind, player_chips[texas.bb_loc])
    game_running = len(active_players) >= 2

    # check game / hand running
    assert texas.is_game_running() == game_running
    assert texas.is_hand_running() == game_running

    if not game_running:
        assert texas.hand_phase == HandPhase.PREHAND
        return

    # check hand_phase
    assert texas.hand_phase == HandPhase.PREFLOP

    # check blind locations
    assert 0 <= texas.btn_loc < texas.max_players

    if len(active_players) > 2:
        assert texas.sb_loc \
               == active_players[(active_players.index(texas.btn_loc) + 1) % len(active_players)]
    else:
        assert texas.btn_loc == texas.sb_loc    # heads up edge case

    assert texas.bb_loc \
           == active_players[(active_players.index(texas.sb_loc) + 1) % len(active_players)]
    assert texas.current_player \
           == active_players[(active_players.index(texas.bb_loc) + 1) % len(active_players)]

    # check blind posting / blind states
    if player_chips[texas.sb_loc] < texas.small_blind:
        assert texas.players[texas.sb_loc].chips == 0   # ALL_IN
        assert texas.players[texas.sb_loc].state == PlayerState.ALL_IN
    else:
        assert texas.players[texas.sb_loc].chips == player_chips[texas.sb_loc] - sb_posted
        assert texas.players[texas.sb_loc].state == PlayerState.TO_CALL

    if player_chips[texas.bb_loc] < texas.big_blind:
        assert texas.players[texas.bb_loc].chips == 0   # ALL_IN
        assert texas.players[texas.bb_loc].state == PlayerState.ALL_IN
    else:
        assert texas.players[texas.bb_loc].chips == player_chips[texas.bb_loc] - bb_posted
        assert texas.players[texas.bb_loc].state == PlayerState.IN

    # other players should not have changed chip count
    assert all(texas.players[i].chips == player_chips[i]
               for i in active_players
               if i not in (texas.sb_loc, texas.bb_loc))

    # check pot is the some of what the sb posted, bb posted, and any starting pot
    assert texas._get_last_pot().get_total_amount() \
           == sb_posted + bb_posted + starting_pot

    # check player states
    # players have TO_CALL
    assert all(texas.players[i].state == PlayerState.TO_CALL
               for i in active_players
               if i not in (texas.sb_loc, texas.bb_loc))

    # if 0 chips skip
    for player_id, chips in enumerate(player_chips, 0):
        if chips == 0:
            assert texas.players[player_id].state == PlayerState.SKIP

    # check chips to call
    assert all(texas.chips_to_call(i) == bb_posted
               for i in active_players
               if i not in (texas.sb_loc, texas.bb_loc))
    assert texas.chips_to_call(texas.sb_loc) == bb_posted - sb_posted
    assert texas.chips_to_call(texas.bb_loc) == 0

    if texas.current_player != texas.sb_loc:
        assert texas.chips_to_call(texas.current_player) == texas.big_blind

    # players have cards
    assert all(len(texas.get_hand(i)) == 2
               for i in active_players)

    # board does not have cards
    assert not texas.board
