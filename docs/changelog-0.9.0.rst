Development
==========================

Features
---------

    - New class :class:`~texasholdem.game.move.MoveIterator` which is a special collection of moves which includes attributes such as :attr:`~texasholdem.game.move.MoveIterator.action_types` and :attr:`~texasholdem.game.move.MoveIterator.raise_range`. Also supports iteration and checking for membership with the :code:`in` operator.
    - New method :meth:`~texasholdem.game.game.TexasHoldEm.get_available_moves()` which returns a :class:`~texasholdem.game.move.MoveIterator` of the available moves for the current player.
