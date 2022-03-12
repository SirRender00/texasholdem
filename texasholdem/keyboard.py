import time

from texasholdem import TexasHoldEm, HandPhase
from texasholdem.gui import TextGUI
from texasholdem.agents import random_agent

game = TexasHoldEm(500, 5, 2, max_players=6)
gui = TextGUI()

user_player_id = 0
gui.set_player_ids([user_player_id])

while game.is_game_running():
    game.start_hand()
    while game.is_hand_running():
        gui.print_state(game)

        if game.current_player == user_player_id:
            action, val = gui.accept_input()
            while not game.validate_move(game.current_player, action, val):
                action, val = gui.accept_input()
        else:
            time.sleep(3)
            action, val = random_agent(game, no_fold=True)

        gui.print_action(game.current_player, action, val)
        game.take_action(action, val)

        if game.hand_phase == HandPhase.SETTLE:
            gui.set_player_ids(range(game.max_players))
            gui.print_state(game)

    game.export_history('./pgns/')
