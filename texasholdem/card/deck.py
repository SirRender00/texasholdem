import random
from texasholdem.card import card
from texasholdem.card.card import Card


class Deck:
    """
    Class representing a deck. The first time we create, we seed the static
    deck with the list of unique card integers. Each object instantiated simply
    makes a copy of this object and shuffles it.

    """
    _FULL_DECK: list[Card] = []

    def __init__(self):
        self.cards = Deck._get_full_deck()
        self.shuffle()

    def shuffle(self) -> None:
        """
        Shuffles the remaining cards in the deck.

        """
        random.shuffle(self.cards)

    def draw(self, num=1) -> list[Card]:
        """
        Draw card(s) from the deck. These cards leave the deck and are not saved.

        Args:
            num (int): How many cards to draw. Defaults to 1.
        Returns:
           list[Card]: A list of length n of cards (See :class:`~texasholdem.card.card.Card`).
        Raises:
            ValueError: If the deck size is less than the given n.

        """
        if len(self.cards) < num:
            raise ValueError(f'Cannot draw {num} cards from deck of size {len(self.cards)}')

        cards = self.cards[:num]
        self.cards = self.cards[num:]
        return cards

    def __str__(self) -> str:
        return card.card_list_to_pretty_str(self.cards)

    @staticmethod
    def _get_full_deck() -> list[Card]:
        if Deck._FULL_DECK:
            return list(Deck._FULL_DECK)

        # create the standard 52 card deck
        for rank in Card.STR_RANKS:
            for suit in Card.CHAR_SUIT_TO_INT_SUIT:
                Deck._FULL_DECK.append(Card(rank + suit))

        return list(Deck._FULL_DECK)
