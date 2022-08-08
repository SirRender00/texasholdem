"""Config for card module tests. Includes:
    - Sample cards
"""
import pytest

from texasholdem.card.deck import Deck


CARDS = (
    ("Kd", int(0b00001000000000000100101100100101)),
    ("5s", int(0b00000000000010000001001100000111)),
    ("Jc", int(0b00000010000000001000100100011101)),
)


@pytest.fixture()
def sample_cards():
    """
    Returns:
        List[Card]: A list of sample cards
    """
    return list(CARDS)


@pytest.fixture()
def deck():
    """
    Returns:
        Deck: A shuffled deck
    """
    return Deck()
