.. _cards:

Cards
========

Instantiation
---------------
To instantiate a :class:`~texasholdem.card.card.Card`, we can pass in a string::

    Card("Kd")

Under the hood, this simply constructs the int representation of the card as the object::

    assert Card("Kd") == 134236965

It is also possible to construct a card from the well-formed int form as described below::

    assert str(Card(134236965)) == "Kd"

Representation
---------------
We represent :class:`~texasholdem.card.card.Card` objects as native Python 32-bit integers. Most of the
bits are used, and have a specific meaning. See below:

.. table:: Card
    :align: center
    :widths: auto

    ========  ========  ========  ========
    xxxbbbbb  bbbbbbbb  cdhsrrrr  xxpppppp
    ========  ========  ========  ========


- p = prime number of rank (in binary) (deuce=2, trey=3, four=5, ..., ace=41)
- r = rank of card (in binary) (deuce=0, trey=1, four=2, five=3, ..., ace=12)
- cdhs = suit of card (bit turned on based on suit of card)
- b = bit turned on depending on rank of card (deuce=1st bit, trey=2nd bit, ...)
- x = unused

**Example**
    .. table::
        :align: center
        :widths: auto

        ================ ========  ========  ========  ========
        Card             xxxAKQJT  98765432  CDHSrrrr  xxPPPPPP
        ================ ========  ========  ========  ========
        King of Diamonds 00001000  00000000  01001011  00100101
        Five of Spades   00000000  00001000  00010011  00000111
        Jack of Clubs    00000010  00000000  10001001  00011101
        ================ ========  ========  ========  ========


This representation allows for minimal memory overhead along with fast applications necessary for poker:

    - Make a unique prime product for each hand (by multiplying the prime bits)
    - Detect flushes (bitwise && for the suits)
    - Detect straights (shift and bitwise &&)

Attributes
------------
Following the representation from above, attributes of the card can be accessed through properties:

    - :attr:`~texasholdem.card.card.Card.rank`
    - :attr:`~texasholdem.card.card.Card.suit`
    - :attr:`~texasholdem.card.card.Card.bitrank`
    - :attr:`~texasholdem.card.card.Card.prime`
    - :code:`str(card)` for the string format (e.g. :code:`str(Card('Kd')) == 'Kd'`)
    - :attr:`~texasholdem.card.card.Card.pretty_string` for a string with ascii suits.

Deck
-----
The :class:`~texasholdem.card.card.Deck` class is a standard collection of the 52 possible Cards. Instantiate a new
deck by simply calling it :code:`Deck()`. The class provides one method :meth:`~texasholdem.card.card.Deck.draw`
which takes an optional parameter :code:`n` and returns that many Cards (default 1).

Card Collection Methods
------------------------
In the :mod:`~texasholdem.card.card` module, there is also a few helper functions that act on collections of cards.

This includes:

    - :func:`~texasholdem.card.card.card_strings_to_int` which transforms a list of strings like
      :code:`str(Card('Kd')) == 'Kd'` into a list of the Card representations.
    - :func:`~texasholdem.card.card.prime_product_from_hand` which takes the prime product of a list of Cards.
    - :func:`~texasholdem.card.card.card_list_to_pretty_str` which returns a string which concatenates the pretty
      strings of each card.
