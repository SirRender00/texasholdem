"""Config for card module tests. Includes:
    - Sample cards
"""
from typing import Tuple

import pytest

from texasholdem.card.deck import Deck


_CARDS = (
    ("Kd", int(0b00001000000000000100101100100101)),
    ("5s", int(0b00000000000010000001001100000111)),
    ("Jc", int(0b00000010000000001000100100011101))
)


@pytest.fixture()
def sample_cards():
    """
    Returns:
        List[Card]: A list of sample cards
    """
    return list(_CARDS)


def get_sample_cards() -> list[Tuple[str, int]]:
    """
    Returns:
        List[Tuple[str, int]]: Sample card strings with their corresponding Card ints.
    """
    return list(_CARDS)


@pytest.fixture()
def deck():
    """
    Returns:
        Deck: A shuffled deck
    """
    return Deck()
