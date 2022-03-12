"""
Config for game tests. Includes:
    - History file with comments
    - Call player fixture
    - And a method containing assert checks for the prehand for a game
"""
import random
from typing import Tuple

import pytest

from texasholdem.game.game import TexasHoldEm
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.action_type import ActionType
from texasholdem.game.player_state import PlayerState

from tests.conftest import GOOD_GAME_HISTORY_DIRECTORY


BASIC_GAME_RUNS = 100
UNTIL_STOP_RUNS = 800


@pytest.fixture()
def history_file_with_comments():
    """
    Returns:
        str: A path to a valid history file with comments
    """
    return GOOD_GAME_HISTORY_DIRECTORY / "call_game_6.pgn"


@pytest.fixture()
def texas_game(request):
    """
    Returns:
        Callable[[...], TexasHoldEm]: Create a TexasHoldEm gain. Fills in default
            values if not given buyin=500, big_blind=5, small_blind=2.
    """
    game = None

    def game_maker(*args, **kwargs):
        nonlocal game
        default_kwargs = {'buyin': 500, 'big_blind': 5, 'small_blind': 2}
        default_kwargs.update(kwargs)
        game = TexasHoldEm(*args, **default_kwargs)
        return game

    yield game_maker

    if request.node.rep_call.failed and game:
        print(game.hand_history.to_string())


@pytest.fixture()
def call_player():
    """
    A player that calls if another player raised or checks.

    """

    def get_action(game: TexasHoldEm) -> Tuple[ActionType, None]:
        player = game.players[game.current_player]
        if player.state == PlayerState.TO_CALL:
            return ActionType.CALL, None
        return ActionType.CHECK, None

    return get_action


@pytest.fixture()
def random_player():
    """
    A uniformly random player:
        - If someone raised, CALL, FOLD, or RAISE with uniform probability
        - Else, CHECK, (FOLD if no_fold=False), RAISE with uniform probability
        - If RAISE, the value will be uniformly random in [min_raise, # of chips]

    """

    def get_action(game: TexasHoldEm, no_fold: bool = False) -> Tuple[ActionType, int]:
        bet_amount = game.player_bet_amount(game.current_player)
        chips = game.players[game.current_player].chips
        min_raise = game.chips_to_call(game.current_player) + bet_amount + game.big_blind
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

        action_type, value = random.choice(possible), None
        if action_type == ActionType.RAISE:
            value = random.randint(min_raise, max_raise)

        return action_type, value

    return get_action


def prehand_checks(texas: TexasHoldEm):
    # pylint: disable=too-many-branches,too-many-statements
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
    assert texas.hand_phase == HandPhase.PREHAND, "Expected HandPhase to be PREHAND"

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
    hand_running = game_running and not texas._is_hand_over()

    assert texas.is_game_running() == game_running, \
        "Expected game to be running iff >= 2 active players"
    assert texas.is_hand_running() == hand_running, \
        "Expected hand to be running iff 2 or more players can take actions"

    if not game_running or not hand_running:
        assert texas.hand_phase == HandPhase.PREHAND, \
            "If game/hand was not running, expected HandPhase to reset to PREHAND"
        return

    # check hand_phase
    assert texas.hand_phase == HandPhase.PREFLOP, \
        "Ran PREHAND, expected next HandPhase to be PREFLOP"

    # check blind locations
    assert 0 <= texas.btn_loc < texas.max_players, \
        f"Expected the blind to be in [0, {texas.max_players})"

    if len(active_players) > 2:
        assert texas.sb_loc \
            == active_players[(active_players.index(texas.btn_loc) + 1) % len(active_players)], \
            "Expected the small blind to be to left of " \
            f"big blind in a {len(active_players)}-player game"
    else:
        assert texas.btn_loc == texas.sb_loc, \
               "Expected the button and small blind to be the same place in a 2-player game"

    assert texas.bb_loc \
           == active_players[(active_players.index(texas.sb_loc) + 1) % len(active_players)], \
           "Expected the big blind to be to the left of the small blind"
    assert texas.current_player \
           == active_players[(active_players.index(texas.bb_loc) + 1) % len(active_players)], \
           "Expected the current player to be to the left of the big blind"

    # check blind posting / blind states
    if player_chips[texas.sb_loc] <= texas.small_blind:
        assert texas.players[texas.sb_loc].chips == 0, \
               "Expected the small blind to post what they have if <= the small blind"
        assert texas.players[texas.sb_loc].state == PlayerState.ALL_IN, \
               "Expected the small blind to be ALL_IN after posting everything"
    else:
        assert texas.players[texas.sb_loc].chips == player_chips[texas.sb_loc] - sb_posted, \
               "Expected the small blind to post exactly the small blind"

        if sb_posted < bb_posted:
            assert texas.players[texas.sb_loc].state == PlayerState.TO_CALL, \
                   "Expected the small blind to have state TO_CALL"
        else:
            assert texas.players[texas.sb_loc].state == PlayerState.IN, \
                   "Expected the small blind who posted more than the big blind to have state IN"

    if player_chips[texas.bb_loc] <= texas.big_blind:
        assert texas.players[texas.bb_loc].chips == 0, \
               "Expected the big blind to post what they have if <= the big blind"
        assert texas.players[texas.bb_loc].state == PlayerState.ALL_IN, \
               "Expected the big blind to be ALL_IN after posting everything"
    else:
        assert texas.players[texas.bb_loc].chips == player_chips[texas.bb_loc] - bb_posted, \
               "Expected the big blind to post exactly the big blind"
        assert texas.players[texas.bb_loc].state == PlayerState.IN, \
               "Expected the big blind to have state IN"

    for i in active_players:
        if i not in (texas.sb_loc, texas.bb_loc):
            assert texas.players[i].chips == player_chips[i], \
                f"Expected player {i} to not have posted anything"

    assert sum(pot.get_total_amount() for pot in texas.pots) \
           == sb_posted + bb_posted + starting_pot, \
           "Expected pot to be the sum of sb posted, bb posted, and any leftover from last round"

    # check player states
    # players have TO_CALL, (we check the small blind above)
    assert all(texas.players[i].state == PlayerState.TO_CALL
               for i in active_players
               if i not in (texas.sb_loc, texas.bb_loc)), \
        "Expected all players to need to call in the pot"

    # if 0 chips skip
    for player_id, chips in enumerate(player_chips, 0):
        if chips == 0:
            assert texas.players[player_id].state == PlayerState.SKIP, \
                   f"Expected player {player_id} with 0 chips to have status SKIP"

    # check chips to call
    for i in active_players:
        if i not in (texas.sb_loc, texas.bb_loc):
            chips_to_call = sum(texas.pots[pot_id].raised - texas.pots[pot_id].get_player_amount(i)
                                for pot_id in range(texas.players[i].last_pot+1))
            assert texas.chips_to_call(i) == chips_to_call, \
                "Expected chips to call to be the raised " \
                "level of the last eligible pot - player amount"

    if texas.players[texas.sb_loc].state != PlayerState.ALL_IN:
        assert texas.chips_to_call(texas.sb_loc) == max(0, bb_posted - sb_posted), \
               "Expected small blind to have to call big_blind - small_blind number of chips"
    assert texas.chips_to_call(texas.bb_loc) == 0, "Expected big blind to have to call 0 chips"

    # players have cards
    assert all(len(texas.get_hand(i)) == 2
               for i in active_players), "Expected all active players to have 2 cards."

    # board does not have cards
    assert not texas.board, "Expected the board to be empty"
