import math

from texasholdem import TexasHoldEm
from texasholdem.card.card import Card
from texasholdem.card.deck import Deck
from texasholdem.game.player_state import PlayerState
from texasholdem.game.action_type import ActionType
from texasholdem.game.hand_phase import HandPhase
from texasholdem.evaluator.evaluator import evaluate
from texasholdem.gui import TextGUI

game = TexasHoldEm(500, 5, 2, max_players=6)
gui = TextGUI()


def _calculate_equity(hand: list[Card], board: list[Card], num_villians: int):
    board_copy = list(board)
    villian_hands: list[list[Card]] = []

    deck = Deck()
    while len(villian_hands) < num_villians:
        villian_hand = []
        while len(villian_hand) < 2:
            c = deck.draw()[0]
            if c not in hand and \
               c not in board_copy and \
               all(c not in v_hand for v_hand in villian_hands):
                villian_hand.append(c)
        villian_hands.append(villian_hand)

    deck = Deck()
    while len(board_copy) < 5:
        c = deck.draw()[0]
        if c not in hand and \
           c not in board_copy and \
           all(c not in v_hand for v_hand in villian_hands):
            board_copy.append(c)

    return 1 if all(evaluate(hand, board_copy) < evaluate(villian_hand, board_copy)
                    for villian_hand in villian_hands) else 0


def calculate_equity(hand: list[Card], board: list[Card], villian_hands: int, n: int = 25000):
    return sum(_calculate_equity(hand, board, villian_hands) for _ in range(n)) / n


def call_player(game: TexasHoldEm):
    player = game.players[game.current_player]
    if player.state == PlayerState.TO_CALL:
        return ActionType.CALL, None
    else:
        return ActionType.CHECK, None


def value_player(game: TexasHoldEm):
    player = game.players[game.current_player]

    chips_at_stake = sum(game._get_pot(i).get_total_amount() for i in range(player.last_pot + 1))
    pot_odds = game.chips_to_call(player.player_id) / chips_at_stake
    equity = calculate_equity(game.get_hand(player.player_id), game.board, len(list(game.active_iter())) - 1)
    value_bet = int(chips_at_stake * equity)

    print(f"pot_odds: {pot_odds}")
    print(f"equity: {equity}")
    print(f"value_bet: {value_bet}")

    if player.state == PlayerState.TO_CALL:
        raise_adjuster = 0.5 * equity - 0.5
        if game.hand_phase == HandPhase.PREFLOP:
            fold_adjuster = math.pow(equity, 1.3) + 0.2
        else:
            fold_adjuster = math.pow(equity, 1.3) - 0.2

        print(f"equity + fold_adjuster: {equity + fold_adjuster}")
        print(f"equity + raise_adjuster: {equity + raise_adjuster}")
        if equity + fold_adjuster < pot_odds:
            return ActionType.FOLD, None
        elif equity + raise_adjuster > pot_odds and value_bet >= 0.25 * chips_at_stake:
            value_bet = max(game.big_blind, value_bet)

            if player.chips <= value_bet:
                return ActionType.ALL_IN, None
            else:
                raise_amt = game.player_bet_amount(player.player_id) + game.chips_to_call(player.player_id) + value_bet
                return ActionType.RAISE, min(raise_amt, player.chips + game.player_bet_amount(player.player_id))
        else:
            return ActionType.CALL, None
    else:
        if equity > pot_odds + 0.05 and value_bet >= 0.25 * chips_at_stake:
            if player.chips <= value_bet:
                return ActionType.ALL_IN, None
            elif value_bet < game.big_blind:
                return ActionType.CHECK, None
            else:
                raise_amt = game.player_bet_amount(player.player_id) + game.chips_to_call(player.player_id) + value_bet
                return ActionType.RAISE, min(raise_amt, player.chips + game.player_bet_amount(player.player_id))
        else:
            return ActionType.CHECK, None


user_player_id = 5
gui.set_player_ids(range(game.max_players))

while game.is_game_running():
    game.start_hand()
    while game.is_hand_running():
        gui.print_state(game)

        if game.hand_phase != HandPhase.SETTLE:
            action_type, val = value_player(game)
            gui.print_action(game.current_player, action_type, val)
            game.take_action(action_type, val)
        else:
            game.take_action(ActionType.CHECK, None)
    game.export_history('./pgns/')
    exit(0)
