"""All tests for the card module

Includes:
    - Tests for the construction of a card (string & int)
    - Tests for all getter attributes of a card
    - Tests for the helper functions of the card module:
        - card_strings_to_int
        - prime_product
        - prime_product_from_rank
"""
import functools
import math

import pytest

from texasholdem.card import card
from texasholdem.card.card import Card
from tests.card.conftest import get_sample_cards


@pytest.mark.parametrize("card_tuple", get_sample_cards())
def test_new_card(card_tuple):
    """
    Test the construction of new cards from a string and from an int.
    """
    card_str, card_int = card_tuple
    assert Card(card_str) == Card(card_int) == card_int, \
        "Expected equivalent constructions to be equal"


@pytest.mark.parametrize("card_tuple", get_sample_cards())
def test_card_rank(card_tuple):
    """
    Rank is the numerical value of the card 0-12, 0 is 2, 12 is A.
    """
    card_str, _ = card_tuple
    assert Card.CHAR_RANK_TO_INT_RANK[card_str[0]] == Card.CHAR_RANK_TO_INT_RANK[card_str[0]]


@pytest.mark.parametrize("card_tuple", get_sample_cards())
def test_card_suit(card_tuple):
    """Test suit getter."""
    card_str, _ = card_tuple
    assert Card(card_str).suit == Card.CHAR_SUIT_TO_INT_SUIT[card_str[1]]


@pytest.mark.parametrize("card_tuple", get_sample_cards())
def test_card_bitrank(card_tuple):
    """Test bitrank getter (bitrank := 2^rank)."""
    card_str, _ = card_tuple
    assert Card(card_str).bitrank == 2 ** Card(card_str).rank


@pytest.mark.parametrize("card_tuple", get_sample_cards())
def test_card_prime(card_tuple):
    """Test prime getter (rank -> prime: 0 -> 2, 1 -> 3, 2 -> 5, ...)"""
    card_str, _ = card_tuple
    assert Card(card_str).prime == Card.PRIMES[Card(card_str).rank]


def test_card_strings_to_int(sample_cards):
    """card_strings_to_int is a helper function for lists of cards"""
    assert set(Card(c[0]) for c in sample_cards) \
           == set(card.card_strings_to_int(c[0] for c in sample_cards))


def test_card_prime_product(sample_cards):
    """prime_product_from_hand is a helper function"""
    assert math.prod(Card(c[0]).prime for c in sample_cards) \
           == card.prime_product_from_hand(Card(c[0]) for c in sample_cards)


def test_card_prime_product_from_rank(sample_cards):
    """prime_product_from_rankbits is a fast, bit-wise helper function"""
    rankbits = functools.reduce(lambda c1, c2: c1 | c2,
                                (Card(c[0]).bitrank for c in sample_cards))
    assert math.prod(Card(c[0]).prime for c in sample_cards) \
           == card.prime_product_from_rankbits(rankbits)
