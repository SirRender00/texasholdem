import random

import pytest

from texasholdem.game.game import TexasHoldEm
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.player_state import PlayerState
from texasholdem.evaluator.evaluator import evaluate


def test_new_game():
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)

    assert texas.is_game_running()
    assert texas.hand_phase == HandPhase.PREHAND
    assert len(texas.players) == 9
    assert all(player.chips == texas.buyin for player in texas.players)


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
    assert texas.hand_phase == HandPhase.PREHAND

    player_chips = [texas.players[i].chips for i in range(texas.max_players)]

    texas.start_hand()

    # should run prehand
    assert texas.is_game_running()
    assert texas.hand_phase == HandPhase.PREFLOP

    # check blind locations
    assert 0 <= texas.btn_loc < texas.max_players
    assert texas.sb_loc == (texas.btn_loc + 1) % texas.max_players
    assert texas.bb_loc == (texas.sb_loc + 1) % texas.max_players
    assert texas.current_player == (texas.bb_loc + 1) % texas.max_players

    # check blind posting
    assert texas.players[texas.sb_loc].chips == player_chips[texas.sb_loc] - texas.small_blind
    assert texas.players[texas.bb_loc].chips == player_chips[texas.bb_loc] - texas.big_blind
    assert all(player.chips == player_chips[player.player_id]
               for player in texas.players
               if player.player_id != texas.sb_loc and player.player_id != texas.bb_loc)
    assert texas._get_last_pot().get_total_amount() == texas.big_blind + texas.small_blind

    # check player states
    assert texas.players[texas.bb_loc].state == PlayerState.IN
    assert all(player.state == PlayerState.TO_CALL
               for player in texas.players
               if player.player_id != texas.bb_loc)

    # players have cards
    assert all(len(texas.get_hand(player.player_id)) == 2 for player in texas.players)

    # board does not have cards
    assert not texas.board


def test_basic_prehand():
    """
    Tests basic state after running 1st prehand

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)
    prehand_checks(texas)


def test_skip_prehand():
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


def test_game_stop_prehand():
    """
    Trying to run a hand when a hand cannot be run won't get passed
    the PREHAND stage and sets texas.game_state to STOPPED

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)
    for player in texas.players:
        player.chips = 0

    # cannot run if only one player has chips
    texas.players[0].chips = 10

    # run PREHAND
    texas.start_hand()

    assert not texas.is_game_running()
    assert not texas.is_hand_running()
    assert texas.hand_phase == HandPhase.PREHAND


@pytest.mark.parametrize('hand_phase,round_num,board_len', [
    (HandPhase.PREFLOP, 1, 0),
    (HandPhase.FLOP, 2, 3),
    (HandPhase.TURN, 3, 4),
    (HandPhase.RIVER, 4, 5)
])
def test_basic_betting_rounds(hand_phase, round_num, board_len, call_player):
    """
    Tests basic state after running the 4 betting rounds.

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)

    seen_players = []

    # run hand until given hand_phase is completed
    texas.start_hand()
    while texas.is_hand_running():
        if texas.hand_phase == hand_phase:
            assert len(texas.board) == board_len
        elif texas.hand_phase == hand_phase.next_phase():
            break

        seen_players.append(texas.current_player)
        texas.take_action(*call_player(texas))

    if hand_phase != HandPhase.RIVER:
        assert texas.hand_phase == hand_phase.next_phase()
    assert texas.is_game_running()

    if hand_phase != HandPhase.RIVER:
        assert texas.is_hand_running()

    # all players took expected number of actions
    assert all(len([i for i in seen_players if i == id]) == round_num
               for id in range(texas.max_players))

    # all players in pot
    assert all(player.state == PlayerState.IN
               for player in texas.players)

    # next player should be sb
    assert texas.current_player == texas.sb_loc

    # should be 30 chips in pot
    assert texas._get_last_pot().get_total_amount() == texas.max_players * texas.big_blind

    if hand_phase != HandPhase.RIVER:  # check chips if not SETTLE phase
        assert all(player.chips == texas.buyin - texas.big_blind for player in texas.players)


def test_basic_settle(call_player):
    """
    Test basic state after running a complete hand: only one winner

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)

    # run complete hand
    random.seed(2)
    texas.start_hand()
    while texas.is_hand_running():
        texas.take_action(*call_player(texas))

    assert texas.is_game_running()
    assert not texas.is_hand_running()

    # find winner
    winner = min(texas.players,
                 key=lambda player: evaluate(texas.get_hand(player.player_id), texas.board))

    assert winner.chips == texas.buyin + (texas.max_players - 1) * texas.big_blind
    assert all(player.chips == texas.buyin - texas.big_blind
               for player in texas.players
               if player != winner)


def test_basic_continuity(call_player):
    """
    Checks basic state continuity between hands

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)
    random.seed(6)

    # run prehand
    texas.start_hand()

    # note the button position
    old_btn_loc = texas.btn_loc

    # run the rest of the hand
    while texas.is_hand_running():
        texas.take_action(*call_player(texas))

    # run 2nd prehand
    texas.start_hand()

    # check btn position is old_btn + 1
    assert texas.btn_loc == (old_btn_loc + 1) % texas.max_players
