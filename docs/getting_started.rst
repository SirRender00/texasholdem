.. _getting_started:

Getting Started
===================

Install
--------
The package is available on pypi and can be installed with::

    pip install texasholdem

For the latest experimental version::

    pip install texasholdem --pre

Quickstart
-----------------
Play a game from the command line and take turns for every player out of the box::

    from texasholdem.game.game import TexasHoldEm
    from texasholdem.gui.text_gui import TextGUI

    game = TexasHoldEm(buyin=500, big_blind=5, small_blind=2, max_players=6)
    gui = TextGUI(game=game)

    while game.is_game_running():
        game.start_hand()

        while game.is_hand_running():
            gui.run_step()

        path = game.export_history('./pgns')     # save history
        gui.replay_history(path)                    # replay history


.. image:: /_static/text_gui_example.gif

Overview
----------
The following is a quick summary of what's in the package. For a thorough explanation of each, see the side bar
or the :ref:`API Reference <api_reference>`.

Game Information
^^^^^^^^^^^^^^^^^^
Get game information and take actions through intuitive attributes::

    from texasholdem import TexasHoldEm, HandPhase, ActionType

    game = TexasHoldEm(buyin=500,
                       big_blind=5,
                       small_blind=2,
                       max_players=9)
    game.start_hand()

    assert game.hand_phase == HandPhase.PREFLOP
    assert HandPhase.PREFLOP.next_phase() == HandPhase.FLOP
    assert game.chips_to_call(game.current_player) == game.big_blind
    assert len(game.get_hand(game.current_player)) == 2

    game.take_action(ActionType.CALL)

    player_id = game.current_player
    game.take_action(ActionType.RAISE, total=10)
    assert game.player_bet_amount(player_id) == 10
    assert game.chips_at_stake(player_id) == 20     # total amount in all pots the player is in

    assert game.chips_to_call(game.current_player) == 10 - game.big_blind

See :ref:`game_information` for more

Cards
^^^^^^^^^^^^^^^^^^
The card module represents cards as 32-bit integers for simple and fast hand
evaluations::

    from texasholdem import Card

    card = Card("Kd")                       # King of Diamonds
    assert isinstance(card, int)            # True
    assert card.rank == 11                  # 2nd highest rank (0-12)
    assert card.pretty_string == "[ K ♦ ]"

See :ref:`cards` for more

Agents
^^^^^^^^^^^^^^^^^^
The package also comes with basic agents including `call_agent` and `random_agent`::

    from texasholdem import TexasHoldEm
    from texasholdem.agents import random_agent, call_agent

    game = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)
    game.start_hand()

    while game.is_hand_running():
        if game.current_player % 2 == 0:
            game.take_action(*random_agent(game))
        else:
            game.take_action(*call_agent(game))

See :ref:`agents` for more

Game History
^^^^^^^^^^^^^^^^^^
Export and import the history of hands to files.::

    from texasholdem import TexasHoldEm
    from texasholdem.gui import TextGUI

    game = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)
    game.start_hand()

    while game.is_hand_running():
        game.take_action(*some_strategy(game))

    # export to file
    game.export_history("./pgns/my_game.pgn")

    # import and replay
    gui = TextGUI()
    gui.replay_history("./pgns/my_game.pgn")

PGN files also support single line and end of line comments starting with "#".

See :ref:`hand history` for more

Poker Evaluator
^^^^^^^^^^^^^^^^^^
The evaluator module returns the rank of the best 5-card hand from a list of 5 to 7 cards.
The rank is a number from 1 (strongest) to 7462 (weakest).::

    from texasholdem import Card
    from texasholdem.evaluator import  evaluate, rank_to_string

    assert evaluate(cards=[Card("Kd"), Card("5d")],
                    board=[Card("Qd"),
                           Card("6d"),
                           Card("5s"),
                           Card("2d"),
                           Card("5h")]) == 927
    assert rank_to_string(927) == "Flush, King High"

See :ref:`evaluator` for more

GUIs
^^^^^^^^^
The GUI package currently comes with a text-based GUI to play & display games from the command line as shown
above, in addition to viewing game history, and playing against agents. Coming later will be web-app based GUIs.

See :ref:`guis` for more
