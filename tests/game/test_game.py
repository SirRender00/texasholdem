"""Tests for the TexasHoldEm class

Includes:
    - Creating a new game
    - Prehand status check
    - SKIP statuses for players with 0 chips
    - 2 player prehand check edge case
    - Blind players having less than a blind = ALL_IN
    - Game cannot continue after trying to run start_hand()
    - Basic betting round status checks for all streets
    - Tests settle status checks

    - Runs a tournament until a winner, simple checks in between each hand
        (number of active players, chips)
    - Tests from history (See the pgn folder for more info)
        - Good PGNs that should not error
        - Bad PGNS that should error when run
"""
import glob
import random

import pytest

from texasholdem.game.game import TexasHoldEm
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.player_state import PlayerState
from texasholdem.evaluator.evaluator import evaluate

from tests.conftest import (strip_comments,
                            GOOD_GAME_HISTORY_DIRECTORY,
                            BAD_GAME_HISTORY_DIRECTORY)

from tests.game.conftest import prehand_checks


def test_new_game():
    """
    Tests the creation of a new game and the starting state.
    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)

    assert texas.is_game_running()
    assert texas.hand_phase == HandPhase.PREHAND
    assert len(texas.players) == 9
    assert all(player.chips == texas.buyin for player in texas.players)


def test_basic_prehand(texas_game):
    """
    Tests basic state after running 1st prehand

    """
    prehand_checks(texas_game)


def test_skip_prehand(call_player):
    """
    Players with 0 chips will have SKIP statuses, blinds should skip
    players with SKIP statuses

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2, max_players=6)
    # 6 players to make this tests invariant to where the button ends up

    # skip every other player
    skip_players = [player for player in texas.players if player.player_id % 2 == 0]
    for player in skip_players:
        player.chips = 0

    # should run prehand
    texas.start_hand()

    # players with 0 chips are skipped
    assert all(player.state == PlayerState.SKIP
               for player in skip_players)

    assert 0 <= texas.btn_loc < texas.max_players
    assert texas.sb_loc == (texas.btn_loc + 2) % texas.max_players
    assert texas.bb_loc == (texas.sb_loc + 2) % texas.max_players

    while texas.is_hand_running():
        assert texas.current_player not in skip_players
        texas.take_action(*call_player(texas))


def test_heads_up_edge_case():
    """
    When only two players are active, the button posts the small blind

    """
    # only two players to start
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2, max_players=2)

    # run PREHAND
    texas.start_hand()

    assert texas.btn_loc == texas.sb_loc
    assert texas.bb_loc == (texas.btn_loc + 1) % texas.max_players
    assert texas.current_player == texas.btn_loc


def test_blind_all_in_prehand():
    """
    If a player has 0 < chips < big blind number of chips, allow them to post what
    they have but be ALL_IN.

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2, max_players=3)
    for player in texas.players:
        player.chips = 1

    # run PREHAND
    texas.start_hand()

    assert texas.players[texas.sb_loc].state == PlayerState.ALL_IN
    assert texas.players[texas.bb_loc].state == PlayerState.ALL_IN


def test_game_stop_prehand(texas_game):
    """
    Trying to run a hand when a hand cannot be run won't get passed
    the PREHAND stage and sets texas.game_state to STOPPED

    """
    for player in texas_game.players:
        player.chips = 0

    # cannot run if only one player has chips
    texas_game.players[0].chips = 10

    # run PREHAND
    texas_game.start_hand()

    assert not texas_game.is_game_running()
    assert not texas_game.is_hand_running()
    assert texas_game.hand_phase == HandPhase.PREHAND


@pytest.mark.parametrize('hand_phase,round_num,board_len', [
    (HandPhase.PREFLOP, 1, 0),
    (HandPhase.FLOP, 2, 3),
    (HandPhase.TURN, 3, 4),
    (HandPhase.RIVER, 4, 5)
])
def test_basic_betting_rounds(hand_phase, round_num, board_len, texas_game, call_player):
    """
    Tests basic state after running the 4 betting rounds.
    """
    # pylint: disable=protected-access
    seen_players = []

    # run hand until given hand_phase is completed
    texas_game.start_hand()
    while texas_game.is_hand_running():
        if texas_game.hand_phase == hand_phase:
            assert len(texas_game.board) == board_len
        elif texas_game.hand_phase == hand_phase.next_phase():
            break

        seen_players.append(texas_game.current_player)
        texas_game.take_action(*call_player(texas_game))

    if hand_phase != HandPhase.RIVER:
        assert texas_game.is_hand_running()
        assert texas_game.hand_phase == hand_phase.next_phase()
    assert texas_game.is_game_running()

    # all players took expected number of actions
    assert all(len([i for i in seen_players if i == player_id]) == round_num
               for player_id in range(texas_game.max_players))

    # all players in pot
    assert all(player.state == PlayerState.IN
               for player in texas_game.players)

    # next player should be sb
    assert texas_game.current_player == texas_game.sb_loc

    # should be 30 chips in pot
    assert texas_game._get_last_pot().get_total_amount() \
           == texas_game.max_players * texas_game.big_blind

    if hand_phase != HandPhase.RIVER:  # check chips if not SETTLE phase
        assert all(player.chips == texas_game.buyin - texas_game.big_blind
                   for player in texas_game.players)


def test_basic_settle(texas_game, call_player):
    """
    Test basic state after running a complete hand: only one winner

    """
    # run complete hand
    random.seed(2)
    texas_game.start_hand()
    while texas_game.is_hand_running():
        texas_game.take_action(*call_player(texas_game))

    assert texas_game.is_game_running()
    assert not texas_game.is_hand_running()

    # find winner
    winner = min(texas_game.players,
                 key=lambda player:
                     evaluate(texas_game.get_hand(player.player_id), texas_game.board))

    assert winner.chips == texas_game.buyin + (texas_game.max_players - 1) * texas_game.big_blind
    assert all(player.chips == texas_game.buyin - texas_game.big_blind
               for player in texas_game.players
               if player != winner)


def test_basic_continuity(texas_game, call_player):
    """
    Checks basic state continuity between hands

    """
    random.seed(6)

    # run prehand
    texas_game.start_hand()

    # note the button position
    old_btn_loc = texas_game.btn_loc

    # run the rest of the hand
    while texas_game.is_hand_running():
        texas_game.take_action(*call_player(texas_game))

    # run 2nd prehand
    prehand_checks(texas_game)

    # check btn position is old_btn + 1
    assert texas_game.btn_loc == (old_btn_loc + 1) % texas_game.max_players


def test_until_stop(call_player):
    """
    Checks state after until one winner

    """
    random.seed(6)
    texas_game = TexasHoldEm(buyin=150, big_blind=5, small_blind=2)

    while True:
        assert sum(player.chips for player in texas_game.players) + texas_game.starting_pot \
               == texas_game.max_players * texas_game.buyin
        prehand_checks(texas_game)

        if not texas_game.is_game_running():
            break

        assert len([player for player in texas_game.players
                    if player.state == PlayerState.SKIP]) < (texas_game.max_players - 1)

        while texas_game.is_hand_running():
            texas_game.take_action(*call_player(texas_game))

    assert len([player for player in texas_game.players
                if player.state == PlayerState.SKIP]) == (texas_game.max_players - 1)
    assert [player for player in texas_game.players
            if player.state != PlayerState.SKIP][0].chips \
           == texas_game.max_players * texas_game.buyin


@pytest.mark.parametrize("pgn", glob.glob(str(GOOD_GAME_HISTORY_DIRECTORY / '*.pgn'),
                                          recursive=True))
def test_good_game_history(pgn):
    """
    Runs the given history and ensures they match the replay
    """
    history_string = strip_comments(pgn)
    last_string = ""
    for state in TexasHoldEm.import_history(pgn):
        last_string = state.hand_history.to_string().strip()
        assert history_string.strip().startswith(state.hand_history.to_string().strip())
    assert history_string.strip() == last_string.strip()


@pytest.mark.parametrize("pgn", glob.glob(str(BAD_GAME_HISTORY_DIRECTORY / '*.pgn'),
                                          recursive=True))
def test_bad_game_history(pgn):
    """
    Runs the given history and ensures it errors.
    """
    with pytest.raises(Exception):
        for _ in TexasHoldEm.import_history(pgn):
            pass
