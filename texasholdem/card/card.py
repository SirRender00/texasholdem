"""
We represent cards as 32-bit integers, so there is no object instantiation -
they are just ints. Most of the bits are used, and have a specific meaning.
See below:

.. table:: Card
    :align: center
    :widths: auto

    ========  ========  ========  ========
    xxxbbbbb  bbbbbbbb  cdhsrrrr  xxpppppp
    ========  ========  ========  ========

- p = prime number of rank (deuce=2,trey=3,four=5,...,ace=41)
- r = rank of card (deuce=0,trey=1,four=2,five=3,...,ace=12)
- cdhs = suit of card (bit turned on based on suit of card)
- b = bit turned on depending on rank of card
(i.e. the least significant bit is turned on if deuce, etc.)
- x = unused

Example:
    .. table::
        :align: center
        :widths: auto

        ========  ========  ========  ========  ================
        xxxAKQJT  98765432  CDHSrrrr  xxPPPPPP  Card
        ========  ========  ========  ========  ================
        00001000  00000000  01001011  00100101  King of Diamonds
        00000000  00001000  00010011  00000111  Five of Spades
        00000010  00000000  10001001  00011101  Jack of Clubs
        ========  ========  ========  ========  ================

This representation will allow us to do very important things like:

- Make a unique prime product for each hand
- Detect flushes
- Detect straights

and is also quite performant.
"""

from __future__ import annotations

import math
from typing import Union, Iterable


class Card(int):
    """
    The 32-bit integer Card as described in the module docstring.
    """

    # the basics
    STR_RANKS = '23456789TJQKA'
    INT_RANKS = tuple(range(13))
    PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)

    # conversion from string => int
    CHAR_RANK_TO_INT_RANK = dict(zip(list(STR_RANKS), INT_RANKS))
    CHAR_SUIT_TO_INT_SUIT = {
        's': 1,  # spades
        'h': 2,  # hearts
        'd': 4,  # diamonds
        'c': 8,  # clubs
    }
    INT_SUIT_TO_CHAR_SUIT = 'xshxdxxxc'

    # for pretty printing
    PRETTY_SUITS = {
        1: "\u2660",  # spades
        2: "\u2665",  # hearts
        4: "\u2666",  # diamonds
        8: "\u2663"  # clubs
    }

    def __new__(cls, arg: Union[str, int]) -> Card:
        """
        Get a binary integer representation of a card, inspired by:

        http://suffe.cool/poker/evaluator.html

        See below:

        .. table:: Card
            :align: center
            :widths: auto

            ========  ========  ========  ========
            xxxbbbbb  bbbbbbbb  cdhsrrrr  xxpppppp
            ========  ========  ========  ========

        - p = prime number of rank (deuce=2,trey=3,four=5,...,ace=41)
        - r = rank of card (deuce=0,trey=1,four=2,five=3,...,ace=12)
        - cdhs = suit of card (bit turned on based on suit of card)
        - b = bit turned on depending on rank of card
        (i.e. the least significant bit is turned on if deuce, etc.)
        - x = unused

        Example:
            "Kd" --> int(0b 00001000  00000000  01001011  00100101) = 134236965

        Args:
            arg (str or int): A representation of a card. (i.e. "Kd" or an already
                well-formed integer like 134236965.)
        Returns:
            Card: The 32bit int representing the card according to above.

        """
        if isinstance(arg, str):
            return Card.from_string(arg)

        return Card.from_int(arg)

    @classmethod
    def from_string(cls, string: str) -> Card:
        """
        Converts Card string to binary integer representation of card, inspired by:

        http://www.suffecool.net/poker/evaluator.html

        Example:
            "Kd" --> int(0b 00001000  00000000  01001011  00100101) = 134236965

        Args:
            string (str): A string representing a card.
        Returns:
            (Card): The 32bit int representing the card as described above
        """

        rank_char = string[0]
        suit_char = string[1]
        rank_int = Card.CHAR_RANK_TO_INT_RANK[rank_char]
        suit_int = Card.CHAR_SUIT_TO_INT_SUIT[suit_char]
        rank_prime = Card.PRIMES[rank_int]

        bitrank = 1 << rank_int << 16
        suit = suit_int << 12
        rank = rank_int << 8

        card_int = bitrank | suit | rank | rank_prime
        return Card.from_int(card_int)

    @classmethod
    def from_int(cls, card_int: int) -> Card:
        """
        Converts an already well-formed card integer (as described in the module
        docstring) into a Card.

        Example:
            134236965 --> Card("Kd")

        Args:
            card_int (int): An int representing a card.
        Returns:
            (Card): The 32bit int representing the card as described above
        """
        return super(Card, cls).__new__(cls, card_int)

    def __str__(self) -> str:
        """
        Translates card into a readable string.

        Example:
            134236965 --> "Kd"

        Returns:
            str: The human-readable string representing this card.

        """
        return Card.STR_RANKS[self.rank] + Card.INT_SUIT_TO_CHAR_SUIT[self.suit]

    def __repr__(self) -> str:
        return f'Card("{str(self)}")'

    @property
    def rank(self) -> int:
        """
        The rank of the card as an int.

        Example:
            134236965 ("Kd") --> 11
            268440327 ("As") --> 12

        Returns:
            int: Number between 0-12, representing the rank of the card.

        """

        return (self >> 8) & 0xF

    @property
    def suit(self) -> int:
        """
        The suit int of the card using the following table:

        .. table::
            :align: center
            :widths: auto

            ========  ======
            Suit      Number
            ========  ======
            Spades      1
            Hearts      2
            Diamonds    4
            clubs       8
            ========  ======

        Example:
            134236965 ("Kd") --> 2

        Returns:
            int: 1,2,4, or 8, representing the suite of the card from the above table.

        """
        return (self >> 12) & 0xF

    @property
    def bitrank(self) -> int:
        """
        The bitrank of the card. This returns 2^k where k is the
        rank of the card.

        Example:
            134236965 ("Kd") --> 2^11

        Returns:
            int: 2^k where k is the rank of the card.

        """
        return (self >> 16) & 0x1FFF

    @property
    def prime(self) -> int:
        """
        Gets the prime associated with the card. This returns the kth prime
        starting at 2 where k is the rank of the card.

        Example:
            134236965 ("Kd") --> 37

        Returns:
            int: The kth prime number (starting at 2) where k is the rank of the card.

        """
        return self & 0x3F

    @property
    def pretty_string(self) -> str:
        """
        Returns:
            string: A human-readable pretty string with ascii suites.

        """
        return f" [ {Card.STR_RANKS[self.rank]} {Card.PRETTY_SUITS[self.suit]} ] "

    @property
    def binary_string(self) -> str:
        """
        For debugging purposes. Displays the binary number as a
        human readable string in groups of four digits.
        """
        bstr = bin(self)[2:][::-1]  # chop off the 0b and THEN reverse string
        output = list("".join(["0000" + "\t"] * 7) + "0000")

        for i, b_char in enumerate(bstr, 0):
            output[i + int(i/4)] = b_char

        # output the string to console
        output.reverse()
        return "".join(output)


def card_strings_to_int(card_strs: Iterable[str]) -> list[Card]:
    """
    Args:
        card_strs (Iterable[str]): An iterable of card strings.
    Returns:
        list[Card]: The cards in the corresponding int format.

    """
    bhand = []
    for card_str in card_strs:
        bhand.append(Card(card_str))
    return bhand


def prime_product_from_hand(cards: Iterable[Card]) -> int:
    """
    Args:
        cards (Iterable[Card]): An Iterable of cards
    Returns:
        int: The product of all primes in the hand, corresponding to the rank of the
            card (See :meth:`Card.prime`)
    """
    return math.prod(card.prime for card in cards)


def prime_product_from_rankbits(rankbits: int) -> int:
    """
    Returns the prime product using the bitrank (b)
    bits of the hand. Each 1 in the sequence is converted
    to the correct prime and multiplied in.

    Primarily used for evaulating flushes and straights,
    two occasions where we know the ranks are *ALL* different.
    Assumes that the input is in form (set bits):

    .. table::
            :align: center
            :widths: auto

            ========  ========
            xxxbbbbb  bbbbbbbb
            ========  ========

    Args:
        rankbits (int): a single 32-bit (only 13-bits set) integer representing
            the ranks of 5 *different* ranked card (5 of 13 bits are set)
    Returns:
        int: The product of all primes in the hand, corresponding
            to the rank of the card.
    """
    product = 1
    for i in Card.INT_RANKS:
        # if the ith bit is set
        if rankbits & (1 << i):
            product *= Card.PRIMES[i]
    return product


def card_list_to_pretty_str(cards: list[Card]) -> str:
    """
    Prints the given card in a human-readable pretty string with
    ascii suites.

    Args:
        cards (list[Card]): A list of card ints in the proper form.
    Returns:
        string: A human-readable pretty string with ascii suites.
    """
    output = " "
    for i, card in enumerate(cards, 0):
        if i != len(cards) - 1:
            output += card.pretty_string + ","
        else:
            output += card.pretty_string + " "

    return output
