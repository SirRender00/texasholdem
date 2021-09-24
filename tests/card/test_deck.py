import pytest

from texasholdem.card.deck import Deck
from texasholdem.card.card import Card


def test_new_deck():
    deck = Deck()
    assert len(set(deck.cards)) == 52
    assert isinstance(deck.cards[0], Card)


def test_draw():
    deck = Deck()

    deck.draw(n=1)
    assert len(deck.cards) == 51

    deck.draw(n=3)
    assert len(deck.cards) == 48

    with pytest.raises(ValueError):
        deck.draw(n=len(deck.cards) + 1)


def test_shuffle():
    assert Deck().cards != Deck().cards, "Expected decks to be shuffled when called"

    deck = Deck()
    cards = list(deck.cards)
    deck.shuffle()
    new_cards = list(deck.cards)
    assert cards != new_cards, "Expected decks to not equal after shuffled"
