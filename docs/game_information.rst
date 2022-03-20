.. _game_information:

Game Information
===================

TexasHoldEm Object
--------------------
The :class:`~texasholdem.game.game.TexasHoldEm` class is the main class of the package which includes complete
functionality to play a game of tournament-style Texas Hold 'Em.

Instantiate
^^^^^^^^^^^^^
To instantiate an instance, we only need to specify the buyin, big blind, and small blind with a default
of 9 players::

    game = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)

Optionally, we can include the number of players::

    game = TexasHoldEm(buyin=500, big_blind=5, small_blind=2, max_players=6)

Playing Hands
^^^^^^^^^^^^^^^
To start playing a hand all we need to call is the :meth:`~texasholdem.game.game.TexasHoldEm.start_hand()` method::

    game.is_hand_running() == False
    game.start_hand()
    game.is_hand_running() == True

Behind the scenes, this method will reset all the pots, move and post the blinds, deal cards, reset the history, etc.
(To see the details, see the :code:`_prehand` function
:source_code:`here <texasholdem/game/game.py#:~:text=def _prehand>`.) We can see how many hands have been
played with the :attr:`~texasholdem.game.game.TexasHoldEm.num_hands` attribute.


Actions
********
To let the current player act we call the :meth:`~texasholdem.game.game.TexasHoldEm.take_action()` method.
For example, :code:`game.take_action(ActionType.CALL)`, or :code:`game.take_action(ActionType.RAISE, 50)`
for a raise action.

Available actions include :obj:`~texasholdem.game.action_type.ActionType.CALL`,
:obj:`~texasholdem.game.action_type.ActionType.ALL_IN`, :obj:`~texasholdem.game.action_type.ActionType.RAISE`,
:obj:`~texasholdem.game.action_type.ActionType.FOLD`, :obj:`~texasholdem.game.action_type.ActionType.CHECK`. See
:class:`~texasholdem.game.action_type.ActionType`.

.. note::
    The action :code:`game.take_action(ActionType.RAISE, 50)` is read raise *to* 50. i.e. the player posts
    the different between what they've already put in the pot and the amount to get to 50.

Canonical Loop
***************
Additionally, with the :meth:`~texasholdem.game.game.TexasHoldEm.is_game_running()` method (which determines if
the game can run any more hands), we now know enough to create a canonical loop (which loops until there is
only one winner). Try it out with one of the basic agents, :func:`~texasholdem.agents.basic.call_agent` or
:func:`~texasholdem.agents.basic.random_agent`::

    while game.is_game_running():
        game.start_hand()
        while game.is_hand_running():
            action, val = random_agent(game)
            print(f"Player {game.current_player} {action} {val}")
            game.take_action(action, val)

General Information
^^^^^^^^^^^^^^^^^^^^^^^

The following notes important attributes. For a full list of attributes, see
:class:`~texasholdem.game.game.TexasHoldEm`.

Buyin & Blind Amounts
***********************
Most of the general information of the game are instance attributes of the class, including the
:attr:`~texasholdem.game.game.TexasHoldEm.buyin`, :attr:`~texasholdem.game.game.TexasHoldEm.big_blind` amount, and
:attr:`~texasholdem.game.game.TexasHoldEm.small_blind` amount.

Blind Locations & Current Player
***********************************
Additionally, there is :attr:`~texasholdem.game.game.TexasHoldEm.btn_loc`,
:attr:`~texasholdem.game.game.TexasHoldEm.sb_loc`, :attr:`~texasholdem.game.game.TexasHoldEm.bb_loc` for the locations
of the blinds given as a number 0 through :attr:`~texasholdem.game.game.TexasHoldEm.max_players` which are seat / player ids
and :attr:`~texasholdem.game.game.TexasHoldEm.current_player` for the id of the current player.

Players
**********
There is also :attr:`~texasholdem.game.game.TexasHoldEm.players` for a list of :attr:`~texasholdem.game.game.Player`
objects indexed by id. More player information can be found under :ref:`Player Information`.

Board & Pots
***************
Further, there is :attr:`~texasholdem.game.game.TexasHoldEm.board` for a list of the communal cards
(See :ref:`Cards <cards>`). Along with :attr:`~texasholdem.game.game.TexasHoldEm.pots` which is a list
of :attr:`~texasholdem.game.game.Pot` objects.

See :ref:`Pot Information`. Note: pot information is more advanced, less relevant, and most methods
will probably be private and refactored in future versions.

Hand Phase & History
**********************
To get the current :class:`~texasholdem.game.hand_phase.HandPhase`, there is the
:attr:`~texasholdem.game.game.TexasHoldEm.hand_phase` attribute. See :ref:`Hand Phases`.

There is the :attr:`~texasholdem.game.game.TexasHoldEm.hand_history` attribute which is a
:obj:`~texasholdem.game.history.History` object and details the entire history of the current hand so far and includes
methods to export / import to files. See :ref:`Hand History`.


.. _hand phases:

Hand Phases
--------------
Hand phases in the texasholdem package include the well-known :obj:`~texasholdem.game.hand_phase.HandPhase.PREFLOP`,
:obj:`~texasholdem.game.hand_phase.HandPhase.FLOP`, :obj:`~texasholdem.game.hand_phase.HandPhase.TURN`, and
:obj:`~texasholdem.game.hand_phase.HandPhase.RIVER` which are referred to as betting rounds.

.. note::
    Additionally, we include the lesser-known :obj:`~texasholdem.game.hand_phase.HandPhase.SETTLE` phase and
    our own :obj:`~texasholdem.game.hand_phase.HandPhase.PREHAND` phase.

Generally, :class:`~texasholdem.game.hand_phase.HandPhase` objects have two attributes of note:

    - :meth:`~texasholdem.game.hand_phase.HandPhase.new_cards()` which describes how many new cards come out that phase
    - :meth:`~texasholdem.game.hand_phase.next_phase()` which returns the next hand phase.

We can get the current hand phase of the game with the :attr:`~texasholdem.game.game.TexasHoldEm.hand_phase` attribute.

The well-known hand phases are self-explanatory so we will briefly touch on the two other phases:

Settle Phase
^^^^^^^^^^^^^
The phase where cards are revealed, hand rank is determined, and chips are rewarded. Currently, there is not a
concept of hidden information implemented and it is up to the developer to implement such a system.
However, in the future we will implement a :code:`View` object which encapsulates public & private information.
Then in this phase, players may choose to :code:`REVEAL` or :code:`MUCK` their cards, allowing other players to see
their cards if they so choose.

Prehand Phase
^^^^^^^^^^^^^^
This phase is the in-between phase between hands. In other words, the game is in an **undefined** state until
:meth:`~texasholdem.game.game.TexasHoldEm.start_hand()` is called again.
:meth:`~texasholdem.game.game.TexasHoldEm.is_hand_running()` will return :code:`False`.


.. _player information:

Player Information
-------------------
Player information can be found in a few locations and is generally found with a :code:`player_id` aka seat id. This
number is a number 0 through :attr:`~texasholdem.game.game.TexasHoldEm.max_players`.

Player Object
^^^^^^^^^^^^^^
The first location we can get basic player information is through the
:attr:`~texasholdem.game.game.TexasHoldEm.players` list (i.e. accessed by :code:`game.players[i]`). This is the
:class:`~texasholdem.game.game.Player` object and includes

    - The :attr:`~texasholdem.game.game.Player.player_id`.
    - The number of :attr:`~texasholdem.game.game.Player.chips` behind a player (i.e. chips not bet or ante'd)
    - The :attr:`~texasholdem.game.game.Player.state` of a player which is of type
      :class:`~texasholdem.game.player_state.PlayerState` and can be one of

        - :obj:`~texasholdem.game.player_state.PlayerState.OUT`, if the player folded this round.
        - :obj:`~texasholdem.game.player_state.PlayerState.SKIP`, if a player cannot play anymore this game.
        - :obj:`~texasholdem.game.player_state.PlayerState.TO_CALL`, if a player needs to put in more chips to continue
          to play.
        - :obj:`~texasholdem.game.player_state.PlayerState.IN`, if a player has posted enough chips to be in the pot
        - :obj:`~texasholdem.game.player_state.PlayerState.ALL_IN`, if a player has posted all their chips (and thus cannot
          take anymore actions).

    - The id of the :attr:`~texasholdem.game.game.Player.last_pot` the player is eligible for.

Chip Counts
^^^^^^^^^^^^
The number of chips that a player currently has behind them as stated above can be found from the
:attr:`~texasholdem.game.game.Player.chips` attribute.

Additionally, the :class:`~texasholdem.game.game.TexasHoldEm` provides a few methods for chip counts:

    - :meth:`~texasholdem.game.game.TexasHoldEm.chips_to_call` returns how many more chips the player needs to
      post to be considered :obj:`~texasholdem.game.player_state.PlayerState.IN`. Note: this is not capped by the
      number of chips the player *can* post. For instance, a player with only 25 chips remaining can still need to
      call >25 chips for the current pot.
    - :meth:`~texasholdem.game.game.TexasHoldEm.player_bet_amount` returns the number of chips the player has bet this
      betting round across all pots.
    - :meth:`~texasholdem.game.game.TexasHoldEm.chips_at_stake` returns how many chips the player can win so far
      (including the chips they've posted as well).

.. _hand history:

Hand History
-------------

The :obj:`~texasholdem.game.history.History` object keeps all necessary information to be able to replay the hand it describes.
It includes an entry for each hand phase, accessible as :code:`history[HandPhase.PREHAND]`, etc. We record the location
of the blinds, player chip counts and cards, etc. for the prehand phase, the new cards and player actions for each
betting round, and finally the winners, hand rank, and win amounts for each pot in the settle phase.

Most usefully, we can export the history to a PGN file with :meth:`~texasholdem.game.game.TexasHoldEm.export_history`.
This will export the history in a human-readable format to a file.

Example PGN File
^^^^^^^^^^^^^^^^^^
.. literalinclude:: ./example_pgn.pgn
    :language: python

.. note::
    By convention, the button is assumed to be player 0 in the PGN format.

.. note::
    Comments starting with '#' is supported in the PGN format.

Replaying Hands
^^^^^^^^^^^^^^^^
We can also import a PGN file with :meth:`~texasholdem.game.game.TexasHoldEm.import_history`. This returns an iterator
over the intermediate states of the game::

    for state in TexasHoldEm.import_history('./texas.pgn'):
        gui.print_state(state)

.. _pot information:

Pot Information
----------------
The pots of the current hand is accessible through the :attr:`~texasholdem.game.game.TexasHoldEm.pots` attribute
which is a list of :attr:`~texasholdem.game.game.Pot` objects (indexable by pot id). Generally, developers
should *not* touch these objects, but can glean some information off of it:

    - :attr:`~texasholdem.game.game.Pot.amount` is the amount in the pot *not* including the current betting round
      (but including any player who folded this betting round).
    - :meth:`~texasholdem.game.game.Pot.get_player_amount` returns the amount the given player has in the pot.

The main pot always has id 0. The :attr:`~texasholdem.game.game.Player.last_pot` attribute on the
:class:`~texasholdem.game.game.Player` object returns the id of the last pot the player is eligible for.
