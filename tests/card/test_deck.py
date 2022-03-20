"""All tests for deck module

Includes:
    - Uniqueness and length of the list of cards
    - Drawing functionality
    - Shuffling
"""
import random

import pytest

from texasholdem.card.deck import Deck
from texasholdem.card.card import Card


def test_new_deck(deck):
    """Test deck creation has all cards"""
    # By merit of the Card class, card integers are valid iff they are well-formed
    # So ensuring the set has 52 members is ensuring that the whole deck is there.
    assert len(set(deck.cards)) == 52, "Expected deck to have 52 unique cards"
    assert len(deck.cards) == 52, "Expected 52 cards in the deck"
    assert all(isinstance(card, Card) for card in deck.cards), \
        "Expected all cards to be of type Card"


def test_draw(deck):
    """Drawing a card properly reduces the amount available in the deck."""
    deck.draw(num=1)
    assert len(deck.cards) == 51, "Expected deck to have one less card after drawing."

    deck.draw(num=3)
    assert len(deck.cards) == 48, "Expected deck to have three less cards after drawing."

    with pytest.raises(ValueError):
        deck.draw(num=len(deck.cards) + 1)


def test_shuffle(deck):
    """
    1. Instantiating a deck should shuffle the cards.
    2. Tests shuffle() method
    """
    random.seed(0)
    assert Deck().cards != Deck().cards, "Expected decks to be shuffled when called"

    cards = list(deck.cards)
    deck.shuffle()
    new_cards = list(deck.cards)
    assert cards != new_cards, "Expected decks to not equal after shuffled"
