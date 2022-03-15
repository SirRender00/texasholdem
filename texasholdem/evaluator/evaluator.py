"""
Evaluates hand strengths with optimizations in terms of speed and memory usage.

"""

import itertools
from texasholdem.card import card
from texasholdem.card.card import Card
from texasholdem.evaluator.lookup_table import LOOKUP_TABLE


def _five(cards: list[Card]) -> int:
    """
    Performs an evaluation given card in integer form, mapping them to
    a rank in the range [1, 7462], with lower ranks being more powerful.

    Variant of Cactus Kev's 5 card evaluator.

    Args:
        cards (list[Card]): A list of 5 card ints.
    Returns:
        int: The rank of the hand.

    """
    # if flush
    if cards[0] & cards[1] & cards[2] & cards[3] & cards[4] & 0xF000:
        hand_or = (cards[0] | cards[1] | cards[2] | cards[3] | cards[4]) >> 16
        prime = card.prime_product_from_rankbits(hand_or)
        return LOOKUP_TABLE.flush_lookup[prime]

    # otherwise
    prime = card.prime_product_from_hand(cards)
    return LOOKUP_TABLE.unsuited_lookup[prime]


def evaluate(cards: list[Card], board: list[Card]) -> int:
    """
    Evaluates the best five-card hand from the given cards and board. Returns
    the corresponding rank.

    Args:
        cards (list[int]): A list of length two of card ints that a player holds.
        board (list[int]): A list of length 3, 4, or 5 of card ints.
    Returns:
        int: A number between 1 (highest) and 7462 (lowest) representing the relative
            hand rank of the given card.

    """
    all_cards = cards + board
    return min([_five(hand) for hand in itertools.combinations(all_cards, 5)])


def get_rank_class(hand_rank: int) -> int:
    """
    Returns the class of hand given the hand hand_rank returned from evaluate from
    9 rank classes.

    Example:
        straight flush is class 1, high card is class 9, full house is class 3.

    Returns:
        int: A rank class int describing the general category of hand from 9 rank classes.
            Example, straight flush is class 1, high card is class 9, full house is class 3.

    """
    max_rank = min(rank
                   for rank in LOOKUP_TABLE.MAX_TO_RANK_CLASS
                   if hand_rank <= rank)
    return LOOKUP_TABLE.MAX_TO_RANK_CLASS[max_rank]


def rank_to_string(hand_rank: int) -> str:
    """
    Returns a string describing the hand of the hand_rank.

    Example:
        166 -> "Four of a Kind"

    Args:
        hand_rank (int): The rank of the hand given by :meth:`evaluate`
    Returns:
        string: A human-readable string of the hand rank (i.e. Flush, Ace High).

    """
    return LOOKUP_TABLE.RANK_CLASS_TO_STRING[get_rank_class(hand_rank)]


def get_five_card_rank_percentage(hand_rank: int) -> float:
    """
    The percentage of how many of the 7462 hand strengths are worse than the given one.

    Args:
        hand_rank (int): The rank of the hand given by :meth:`evaluate`
    Returns:
        float: The percentile strength of the given hand_rank (i.e. what percent of hands is worse
            than the given one).

    """
    return 1 - float(hand_rank) / float(LOOKUP_TABLE.MAX_HIGH_CARD)
