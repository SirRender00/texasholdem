texasholdem |release|
=======================

.. toctree::
   :hidden:

   getting_started
   game_information
   agents
   cards
   guis
   evaluator
   reference
   changelog

A python package for Texas Hold 'Em Poker, providing

    - Fast evaluation of hand strengths
    - Export & import human-readable game history
    - GUIs to view games and game history
    - Simple & complex agents
    - Compliance with World Series of Poker Official Rules
    - And more

See the source code for this version :source_code:`on github <.>`

Getting Started
-----------------
To get started see :ref:`Getting Started <getting_started>`.

Contributing
---------------
Want a new feature, found a bug, or have questions? Feel free to add to our issue board on Github!
`Open Issues <https://github.com/SirRender00/texasholdem/issues>`_.

We welcome any developer who enjoys the package enough to contribute! Please message me at evyn.machi@gmail.com
if you want to be added as a contributor and check out the
`Developer's Guide <https://github.com/SirRender00/texasholdem/wiki/Developer's-Guide>`_.

What's New in |release|
------------------------

Features
^^^^^^^^^

    - New class :class:`~texasholdem.game.move.MoveIterator` which is a special collection of moves which includes attributes such as :attr:`~texasholdem.game.move.MoveIterator.action_types` and :attr:`~texasholdem.game.move.MoveIterator.raise_range`. Also supports iteration and checking for membership with the :code:`in` operator. Use the :meth:`~texasholdem.game.move.MoveIterator.sample()` method to sample from the collection.
    - New method :meth:`~texasholdem.game.game.TexasHoldEm.get_available_moves()` which returns a :class:`~texasholdem.game.move.MoveIterator` of the available moves for the current player.
