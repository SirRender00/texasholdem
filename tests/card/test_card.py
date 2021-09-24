import functools
import math
from typing import Tuple

import pytest

from texasholdem.card import card
from texasholdem.card.card import Card

cards: list[Tuple[str, int]] = [
    ("Kd", int(0b00001000000000000100101100100101)),
    ("5s", int(0b00000000000010000001001100000111)),
    ("Jc", int(0b00000010000000001000100100011101))
]


@pytest.mark.parametrize("card_tuple", cards)
def test_new_card(card_tuple):
    card_str, card_int = card_tuple
    assert Card(card_str) == Card(card_int) == card_int


@pytest.mark.parametrize("card_tuple", cards)
def test_card_rank(card_tuple):
    card_str, _ = card_tuple
    assert Card(card_str).rank == Card.CHAR_RANK_TO_INT_RANK[card_str[0]]


@pytest.mark.parametrize("card_tuple", cards)
def test_card_suit(card_tuple):
    card_str, _ = card_tuple
    assert Card(card_str).suit == Card.CHAR_SUIT_TO_INT_SUIT[card_str[1]]


@pytest.mark.parametrize("card_tuple", cards)
def test_card_bitrank(card_tuple):
    card_str, _ = card_tuple
    assert Card(card_str).bitrank == 2 ** Card(card_str).rank


@pytest.mark.parametrize("card_tuple", cards)
def test_card_prime(card_tuple):
    card_str, _ = card_tuple
    assert Card(card_str).prime == Card.PRIMES[Card(card_str).rank]


def test_card_strings_to_int():
    assert set(Card(c[0]) for c in cards) == set(card.card_strings_to_int(c[0] for c in cards))


def test_card_prime_product():
    assert math.prod(Card(c[0]).prime for c in cards) == card.prime_product_from_hand(Card(c[0]) for c in cards)


def test_card_prime_product_from_rank():
    rankbits = functools.reduce(lambda c1, c2: c1 | c2, (Card(c[0]).bitrank for c in cards))
    assert math.prod(Card(c[0]).prime for c in cards) == card.prime_product_from_rankbits(rankbits)
