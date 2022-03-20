"""
The lookup table module keeps the books on all possible hand strengths.
We construct the table once on import and reference it repeatedly.

Number of Distinct Hand Values::

    Straight Flush   10
    Four of a Kind   156      [(13 choose 2) * (2 choose 1)]
    Full Houses      156      [(13 choose 2) * (2 choose 1)]
    Flush            1277     [(13 choose 5) - 10 straight flushes]
    Straight         10
    Three of a Kind  858      [(13 choose 3) * (3 choose 1)]
    Two Pair         858      [(13 choose 3) * (3 choose 2)]
    One Pair         2860     [(13 choose 4) * (4 choose 1)]
    High card      + 1277     [(13 choose 5) - 10 straights]
    -------------------------
    TOTAL            7462

Here we create a lookup table which maps:

    - 5 card hand's unique prime product -> rank in range [1, 7462]

Example:
    - Royal flush (best hand possible) -> 1
    - 7-5-4-3-2 unsuited (worst hand possible) -> 7462

"""

from typing import Dict
import itertools

from texasholdem.card import card
from texasholdem.card.card import Card


class LookupTable:
    # pylint: disable=too-few-public-methods
    """
    Attributes:
        flush_lookup (dict[int, int]): map from prime-product to rank for suited cards
        unsuited_lookup (dict[int, int]): map from prime-product to rank for unsuited cards

    """

    MAX_STRAIGHT_FLUSH = 10
    MAX_FOUR_OF_A_KIND = 166
    MAX_FULL_HOUSE = 322
    MAX_FLUSH = 1599
    MAX_STRAIGHT = 1609
    MAX_THREE_OF_A_KIND = 2467
    MAX_TWO_PAIR = 3325
    MAX_PAIR = 6185
    MAX_HIGH_CARD = 7462

    MAX_TO_RANK_CLASS = {
        MAX_STRAIGHT_FLUSH: 1,
        MAX_FOUR_OF_A_KIND: 2,
        MAX_FULL_HOUSE: 3,
        MAX_FLUSH: 4,
        MAX_STRAIGHT: 5,
        MAX_THREE_OF_A_KIND: 6,
        MAX_TWO_PAIR: 7,
        MAX_PAIR: 8,
        MAX_HIGH_CARD: 9
    }

    RANK_CLASS_TO_STRING = {
        1: "Straight Flush",
        2: "Four of a Kind",
        3: "Full House",
        4: "Flush",
        5: "Straight",
        6: "Three of a Kind",
        7: "Two Pair",
        8: "Pair",
        9: "High card"
    }

    def __init__(self):
        # create dictionaries
        self.flush_lookup: Dict[int, int] = {}
        self.unsuited_lookup: Dict[int, int] = {}

        # create the lookup table in piecewise fashion
        self._flushes()  # this will call straights and high card method,
        # we reuse some of the bit sequences
        self._multiples()

    def _flushes(self):
        """
        Straight flushes and flushes.

        Lookup is done on 13 bit integer (2^13 > 7462):
        xxxbbbbb bbbbbbbb => integer hand index

        """

        # straight flushes in rank order
        straight_flushes = [
            7936,  # int('0b1111100000000', 2), # royal flush
            3968,  # int('0b111110000000', 2),
            1984,  # int('0b11111000000', 2),
            992,  # int('0b1111100000', 2),
            496,  # int('0b111110000', 2),
            248,  # int('0b11111000', 2),
            124,  # int('0b1111100', 2),
            62,  # int('0b111110', 2),
            31,  # int('0b11111', 2),
            4111  # int('0b1000000001111', 2) # 5 high
        ]

        # now we'll dynamically generate all the other
        # flushes (including straight flushes)
        flushes = []
        gen = LookupTable._get_lexographically_next_bit_sequence(int('0b11111', 2))

        # 1277 = number of high card
        # 1277 + len(str_flushes) is number of hands with all card unique rank
        for _ in range(1277 + len(straight_flushes) - 1):  # we also iterate over SFs
            # pull the next flush pattern from our generator
            flush = next(gen)

            # if this flush matches perfectly any
            # straight flush, do not add it
            not_sf = True
            for straight_flush in straight_flushes:
                # if f XOR sf == 0, then bit pattern
                # is same, and we should not add
                if not flush ^ straight_flush:
                    not_sf = False

            if not_sf:
                flushes.append(flush)

        # we started from the lowest straight pattern, now we want to start ranking from
        # the most powerful hands, so we reverse
        flushes.reverse()

        # now add to the lookup map:
        # start with straight flushes and the rank of 1
        # since theyit is the best hand in poker
        # rank 1 = Royal Flush!
        rank = 1
        for straight_flush in straight_flushes:
            prime_product = card.prime_product_from_rankbits(straight_flush)
            self.flush_lookup[prime_product] = rank
            rank += 1

        # we start the counting for flushes on max full house, which
        # is the worst rank that a full house can have (2,2,2,3,3)
        rank = LookupTable.MAX_FULL_HOUSE + 1
        for flush in flushes:
            prime_product = card.prime_product_from_rankbits(flush)
            self.flush_lookup[prime_product] = rank
            rank += 1

        # we can reuse these bit sequences for straights
        # and high card since they are inherently related
        # and differ only by context
        self._straight_and_highcards(straight_flushes, flushes)

    def _straight_and_highcards(self, straights, highcards):
        """
        Unique five card sets. Straights and highcards.

        Reuses bit sequences from flush calculations.
        """
        rank = LookupTable.MAX_FLUSH + 1

        for straight in straights:
            prime_product = card.prime_product_from_rankbits(straight)
            self.unsuited_lookup[prime_product] = rank
            rank += 1

        rank = LookupTable.MAX_PAIR + 1
        for high_card in highcards:
            prime_product = card.prime_product_from_rankbits(high_card)
            self.unsuited_lookup[prime_product] = rank
            rank += 1

    def _multiples(self):
        # pylint: disable=too-many-locals
        """
        Pair, Two Pair, Three of a Kind, Full House, and 4 of a Kind.
        """
        backwards_ranks = range(len(Card.INT_RANKS) - 1, -1, -1)

        # 1) Four of a Kind
        rank = LookupTable.MAX_STRAIGHT_FLUSH + 1

        # for each choice of a set of four rank
        for i in backwards_ranks:

            # and for each possible kicker rank
            kickers = list(backwards_ranks[:])
            kickers.remove(i)
            for k in kickers:
                product = Card.PRIMES[i] ** 4 * Card.PRIMES[k]
                self.unsuited_lookup[product] = rank
                rank += 1

        # 2) Full House
        rank = LookupTable.MAX_FOUR_OF_A_KIND + 1

        # for each three of a kind
        for i in backwards_ranks:

            # and for each choice of pair rank
            pair_ranks = list(backwards_ranks[:])
            pair_ranks.remove(i)
            for pair_rank in pair_ranks:
                product = Card.PRIMES[i] ** 3 * Card.PRIMES[pair_rank] ** 2
                self.unsuited_lookup[product] = rank
                rank += 1

        # 3) Three of a Kind
        rank = LookupTable.MAX_STRAIGHT + 1

        # pick three of one rank
        for b_rank in backwards_ranks:

            kickers = list(backwards_ranks[:])
            kickers.remove(b_rank)

            for kickers in itertools.combinations(kickers, 2):
                card1, card2 = kickers
                product = Card.PRIMES[b_rank] ** 3 * Card.PRIMES[card1] * Card.PRIMES[card2]
                self.unsuited_lookup[product] = rank
                rank += 1

        # 4) Two Pair
        rank = LookupTable.MAX_THREE_OF_A_KIND + 1

        for two_pair in itertools.combinations(backwards_ranks, 2):

            pair1, pair2 = two_pair
            kickers = list(backwards_ranks[:])
            kickers.remove(pair1)
            kickers.remove(pair2)
            for kicker in kickers:
                product = Card.PRIMES[pair1] ** 2 * Card.PRIMES[pair2] ** 2 * Card.PRIMES[kicker]
                self.unsuited_lookup[product] = rank
                rank += 1

        # 5) Pair
        rank = LookupTable.MAX_TWO_PAIR + 1

        # choose a pair
        for pairrank in backwards_ranks:

            kickers = list(backwards_ranks[:])
            kickers.remove(pairrank)

            for kickers in itertools.combinations(kickers, 3):
                kicker1, kicker2, kicker3 = kickers
                product = Card.PRIMES[pairrank] ** 2 * Card.PRIMES[kicker1] \
                    * Card.PRIMES[kicker2] * Card.PRIMES[kicker3]
                self.unsuited_lookup[product] = rank
                rank += 1

    @staticmethod
    def _get_lexographically_next_bit_sequence(bits):
        """
        Bit hack from here:
        http://www-graphics.stanford.edu/~seander/bithacks.html#NextBitPermutation

        Generator even does this in poker order rank
        so no need to sort when done!
        """
        xbits = (bits | (bits - 1)) + 1
        lexo_next = xbits | ((((xbits & -xbits) // (bits & -bits)) >> 1) - 1)
        yield lexo_next
        while True:
            xbits = (lexo_next | (lexo_next - 1)) + 1
            lexo_next = xbits | ((((xbits & -xbits) // (lexo_next & -lexo_next)) >> 1) - 1)
            yield lexo_next


LOOKUP_TABLE = LookupTable()
"""
The lookup table that is created when imported
"""
