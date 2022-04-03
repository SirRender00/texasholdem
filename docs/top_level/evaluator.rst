.. _evaluator:

Hand Evaluator
=====================
The :mod:`~texasholdem.game.evaluator.evaluator` module includes functions that quickly determine hand
rank (out of the possible 7462 hand strengths), to display that information in a human-readable format,
and -- in the future -- to quickly determine the probabilities of winning an incomplete hand
(i.e. odds of winning preflop, turn, etc.).

Usage
------
The main function of this module is the :func:`~texasholdem.evaluator.evaluator.evaluate` function, which
takes two arguments: the two-card hand to evaluate and the communal board (of three, four, or five cards),
and returns a number 1 (strongest) thru 7462 (weakest) which is the hand rank.

.. note::
    In the future, optimization of the board cards vs the hand cards will be implemented so it is best practice
    to separate them when calling the function.

To make this number humanized, the module includes the
:func:`~texasholdem.game.evaluator.rank_to_string` function which takes a hand rank and prints it. Example::

      rank_to_string(166) == "Four of a Kind"

Note: this only considers *made* hands and does not factor any kind of probability.

Probability Evaluation
-----------------------
As of right now, the only function towards probability evaluation is the
:func:`~texasholdem.game.evaluator.get_five_card_rank_percentage` which takes a hand rank and returns how many
hand ranks that it beats. (i.e. calculates :code:`1 - hand_rank / 7462`)

Implementation
----------------

Evaluate
^^^^^^^^^
Behind the hood, the :func:`~texasholdem.game.evaluator.evaluator.evaluate` function performs a lookup of the prime
product of the given cards with a pre-computed lookup table that is generated in constant time complexity
on module import.

Currently, to determine the best 5-card hand out of 7 cards, we take the best rank of every
5-card combination. In the future, we will take advantage of shared cards and pruning to optimize this further.

Lookup Table
^^^^^^^^^^^^^
The general outline of how this lookup table is generated is laid out below.

We split the generation into a few classes: (suited) straights, flushes, and combinations. For (suited) straights,
we can begin generating by assigning the highest rank class to the highest combination (Ace to Ten straight)
and then walking down and assigning the next rank. For combinations, we choose the multiples and then iterate
over the kicker combinations. For flushes and high cards, we take all rank combinations that aren't a straight
or combo.

.. note::
    There is no discernible difference between suited and unsuited generation other than suited is a few rank
    classes higher.

With added optimizations to take advantage of many similarities to avoid repeat work, this comes out to constant
time generation in the number of hand strengths (7462) and hand ranks (13).

See the :mod:`~texasholdem.game.evaluator.evaluator.lookup_table` for details.
