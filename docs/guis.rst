.. _guis:

GUIs
========

Presently, the package provides only one GUI. Future versions would most likely include extra submodules that
will make it possible to download and use other versions (i.e. a web-based one).

Text GUI
--------------
The :class:`~texasholdem.gui.text_gui.TextGUI..TextGUI` class uses Std Out and Std In to accept input and print the board state.
The Text GUI only support games with 6 players but the GUI will be refactored and improved shortly.

The GUI is independent of game instance and provides a few methods to display the game and print actions:

    - :meth:`~texasholdem.gui.text_gui.TextGUI.print_state` prints the state of the game.
    - :meth:`~texasholdem.gui.text_gui.TextGUI.print_action` prints the last action of the game.
    - :meth:`~texasholdem.gui.text_gui.TextGUI.accept_input` takes input from Std In and outputs the well-formed action tuple
      for use in :meth:`~texasholdem.game.game.TexasHoldEm.take_action` For example

        - :code:`raise 50 --> (ActionType.RAISE, 50)`
        - :code:`RAISE 50 --> (ActionType.RAISE, 50)`
        - :code:`CALL --> (ActionType.CALL, None)`

    - :meth:`~texasholdem.gui.text_gui.TextGUI.set_player_ids` takes an iterable of player ids and configures which
      players' cards should be printed out with :meth:`~texasholdem.gui.text_gui.TextGUI.print_state`
