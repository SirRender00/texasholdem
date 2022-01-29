"""
Config module for the evaluator tests includes:
    - Constants for how many times to run the fuzz testing
    - Truth constants
    - Generation tools for creating hands of a certain class with
        a certain board.
"""
import itertools
from typing import Optional
import random

from texasholdem.card.card import Card


MAX_HAND_RANK = 7462
FUZZ_COMPARE_WITH_BOARD = 100
GETTER_CONVENIENCE_RUNS = 100
ALL_SUITS = tuple(Card.CHAR_SUIT_TO_INT_SUIT.keys())


def is_flush(cards: list[Card]) -> bool:
    """
    Arguments:
        cards (list[Card]): The hand to use
    Returns:
        bool: True if there exists a five-card hand combo in the given cards
            that results in a flush, False o/w
    """
    if len(cards) < 5:
        return False

    return any(bool(hand[0] & hand[1] & hand[2] & hand[3] & hand[4] & 0xF000)
               for hand in itertools.combinations(cards, 5))


def find_nonflush_suit(suits: Optional[list[str]] = None) -> str:
    """
    Arguments:
        suits (Optional[list[str]]): The suits to use, default None
    Returns:
        str: A suit such that suits + [suit] is not a flush
    Raises:
        ValueError: If such a suit does not exist
    """
    suits = [] if not suits else suits
    suit_choices = list(ALL_SUITS)
    suit_candidate = random.choice(suit_choices)

    ranks = random.sample(Card.STR_RANKS, k=len(suits)+1)
    while is_flush([Card(rank + suit) for rank, suit in zip(ranks, suits + [suit_candidate])]):
        suit_choices.remove(suit_candidate)

        if not suit_choices:
            raise ValueError(f"Can only form a flush with suits {suits}.")

        suit_candidate = random.choice(suit_choices)

    return suit_candidate


def generate_nonflush_suits(board: Optional[list[Card]] = None) -> list[str]:
    """
    Arguments:
        board (Optional[List[Card]]): The board to use of length 3, 4, or 5 (default None).
    Returns:
        List[str]: A list of 5 uniformly random suits that are not a flush (2 if board is given).
    Raises:
        ValueError: If the board given is already a flush.
    """
    board = [] if not board else board
    if is_flush(board):
        raise ValueError("Board is already a flush.")

    board_suits = [Card.INT_SUIT_TO_CHAR_SUIT[car.suit] for car in board]

    suits = []
    for _ in range(5 if not board else 2):
        suits.append(find_nonflush_suit(suits + board_suits))
    return suits


def is_straight(ranks: list[int]) -> bool:
    """
    Arguments:
        ranks (List[int]): The ranks to use
    Returns:
        bool: True if there exists a five-card hand combo in the given cards
            that results in a straight, False o/w
    """
    if len(ranks) < 5:
        return False

    ranks = list(ranks)
    if Card.INT_RANKS[-1] in ranks:
        ranks.append(Card.INT_RANKS[0] - 1)

    return any(sorted(hand) == list(range(min(hand), max(hand) + 1))
               for hand in itertools.combinations(ranks, 5))


def find_nonstraight_rank(ranks: list[int]) -> int:
    """
    Arguments:
        ranks (List[int]): a list of ranks
    Returns:
        int: a rank such that any 5-card hand does not form a straight (or any other combo)
    Raises:
        ValueError: If a rank could not be found.
    """
    rank_choices = list(Card.INT_RANKS)
    for rank in set(ranks):
        rank_choices.remove(rank)

    rank_cand = random.choice(rank_choices)

    while is_straight(ranks + [rank_cand]):
        rank_choices.remove(rank_cand)
        if not rank_choices:
            raise ValueError(f"Can only form a straight with ranks {ranks}.")
        rank_cand = random.choice(rank_choices)

    return rank_cand


def get_rank_counts(rank_list: list[int]) -> dict[int, int]:
    """
    Arguments:
        rank_list (List[int]): A list of ranks
    Returns:
        Dict[int, int]: An ordered dictionary from rank -> count where the keys are ordered
            by descending count then descending rank.
    """
    counts = {}
    for rank in rank_list:
        counts[rank] = counts.get(rank, 0) + 1

    counts = dict(sorted(counts.items(), key=lambda item: item[0], reverse=True))
    counts = dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))
    return counts


def less_hands_same_class(rank_class: int, hand1: list[Card], hand2: list[Card]) -> bool:
    """
    Compares two hands from the same rank_class against each other, returning True if
    hand1 loses against hand2, False otherwise.

    Arguments:
        rank_class (int): The rank class
        hand1 (List[Card]): The first hand
        hand2 (List[Card]): The second hand
    Returns:
        bool: True if hand1 loses against hand2, False otherwise.
    """
    ranks1, ranks2 = [car.rank for car in hand1], [car.rank for car in hand2]

    # straight flushes or straights, fix ace to be "-1" instead of 12
    if rank_class in (1, 5):
        for ranks in (ranks1, ranks2):
            if Card.INT_RANKS[-1] in ranks and Card.INT_RANKS[0] in ranks:
                ranks.remove(Card.INT_RANKS[-1])
                ranks.append(Card.INT_RANKS[0] - 1)

    # Sort the unique ranks by count then rank, reduces to list compare
    counts1, counts2 = get_rank_counts(ranks1), get_rank_counts(ranks2)
    return list(counts1.keys()) < list(counts2.keys())


def generate_nonstraight_noncombo(board: Optional[list[Card]] = None) -> list[str]:
    """
    Arguments:
        board (Optional[List[Card]]): The board to use of length 3, 4, or 5 (default None).
    Returns:
        List[str]: A list of two str ranks (or five if board is None)
            that don't form a straight or any combo when combined with the board
    Raises:
        ValueError: If a straight could not be formed or if the board contains a combo.
    """
    board = [] if not board else board
    board_ranks = [car.rank for car in board]

    if any(count >= 2 for count in get_rank_counts(board_ranks).values()):
        raise ValueError("Board contains a combo.")

    ranks = []
    for _ in range(5 if not board else 2):
        rank = find_nonstraight_rank(ranks + board_ranks)
        ranks.append(rank)

    return [Card.STR_RANKS[rank] for rank in ranks]


def generate_straight(board: Optional[list[Card]] = None) -> list[str]:
    """
    Arguments:
        board (Optional[List[Card]]): The board to use of length 3, 4, or 5 (default None).
    Returns:
        List[str]: A list of two str ranks (or five if board is None)
            that form a straight when combined with the board
    Raises:
        ValueError: If it's impossible to generate a straight
    """
    if not board:
        high = random.choice(range(Card.STR_RANKS.index('5'),
                                   Card.STR_RANKS.index('A')))
        return [Card.STR_RANKS[i % len(Card.INT_RANKS)] for i in range(high, high - 5, -1)]

    board_ranks = [car.rank for car in board]
    if Card.INT_RANKS[-1] in board_ranks:
        board_ranks.append(Card.INT_RANKS[0] - 1)

    rank_choices = [rank for rank in Card.INT_RANKS if rank not in board_ranks]

    for ranks in itertools.combinations(rank_choices, 2):
        for hand in itertools.combinations(board_ranks + list(ranks), 5):
            if is_straight(list(hand)):
                return list(Card.STR_RANKS[rank] for rank in ranks)

    raise ValueError("Could not generate a straight.")


def generate_flush(board: Optional[list[Card]] = None) -> list[str]:
    """
    Arguments:
        board (Optional[List[Card]]): The board to use of length 3, 4, or 5 (default None).
    Returns:
        List[str]: A list of two str suites (or five if board is None)
            that form a flush when combined with the board
    Raises:
        ValueError: If it's impossible to generate a flush
    """
    if not board:
        return 5 * [random.choice(ALL_SUITS)]

    suit_counts = {}
    for car in board:
        suit_counts[car.suit] = suit_counts.get(car.suit, 0) + 1

    suit_choices = [suit for suit, count in suit_counts.items() if count >= 3]
    if not suit_choices:
        raise ValueError("Impossible to form flush with given board.")

    return 2 * [Card.INT_SUIT_TO_CHAR_SUIT[suit_choices[0]]]


def generate_combo(*combos: int, board: Optional[list[Card]] = None) -> list[Card]:
    """
    Easy generation of combos, examples below give a clearer picture:

    Example:
        `generate_combo(3, 2)` -> Full House
        `generate_combo(2, 2, 1)` -> Two Pair
        `generate_combo(3, 1, 1)` -> Three of a Kind

    This function also ensures proper suits.

    Arguments:
        combos (int): How many cards to put in this same-rank grouping,
            The number of ints given determines the quantity of rank-disjoint groupings
        board (Optional[List[Card]]): The board to use of length 3, 4, or 5 (default None).
    Returns:
        List[Card]: A uniformly random five-card hand (or two-card hand if board is given)
            conforming to the combos given (when combined with the board).
    Raises:
        ValueError: If any combos-integer given exceeds 4, or if len(combos) > 13
    """
    if any(combo > 4 for combo in combos):
        raise ValueError("Cannot put more than 4 ranks in a grouping")

    if len(combos) > len(Card.STR_RANKS):
        raise ValueError("Cannot create more than 13 groups")

    board = [] if not board else board
    num_cards = 5 if not board else 2

    def find_edit_distance_within(rank_dict, combos_list, distance=2):
        """
        Shuffles through the permutations of combos list such that
        the sum of the differences of the counts between rank_dict and combos_list
        is less than or equal to 2 (i.e. 2 cards added to rank_dict could
        make it conform to the combos).
        """
        for combo_list in itertools.combinations(combos_list, len(combos_list)):
            candidate_zipped = list(itertools.zip_longest(rank_dict.values(),
                                                          combo_list,
                                                          fillvalue=0))

            total = 0
            for board_num_, combo_num_ in candidate_zipped:
                if board_num_ < combo_num_:
                    total += combo_num_ - board_num_

            if total <= distance:
                return candidate_zipped

        raise ValueError("Could not make combo with given board.")

    combos = list(combos)
    board_rank_dict = get_rank_counts([car.rank for car in board])

    if any(combo_count < board_count
           for combo_count, board_count in itertools.zip_longest(sorted(combos, reverse=True),
                                                                 board_rank_dict.values(),
                                                                 fillvalue=1)):
        raise ValueError("Board has a higher combo than the given combo.")

    ranks = []
    combo_within = find_edit_distance_within(board_rank_dict, combos, distance=num_cards)

    for rank, (board_num, combo_num) in itertools.zip_longest(list(board_rank_dict.keys()),
                                                              combo_within,
                                                              fillvalue=-1):
        # In a group that is lacking, add the required rank
        if combo_num > board_num:
            if rank == -1:
                rank = find_nonstraight_rank(list(board_rank_dict.keys()) + ranks)

            ranks += (combo_num - board_num) * [rank]

    # if we did not add two cards, add the rest (taking out already chosen ranks)
    for _ in range(num_cards - len(ranks)):
        ranks.append(find_nonstraight_rank(list(board_rank_dict.keys()) + ranks))

    # finally add suits to the new ranks (take out the suits in the same group)
    cards = []
    for rank in ranks:
        same_rank_cards = [car for car in board + cards if car.rank == rank]
        suit_choices = [suit for suit in ALL_SUITS
                        if suit not in
                        [Card.INT_SUIT_TO_CHAR_SUIT[car.suit] for car in same_rank_cards]]

        suit_candidate = random.choice(suit_choices)
        while is_flush(board + cards + [Card(Card.STR_RANKS[rank] + suit_candidate)]):
            suit_choices.remove(suit_candidate)
            suit_candidate = random.choice(suit_choices)
        cards.append(Card(Card.STR_RANKS[rank] + suit_candidate))

    return cards


def generate_sample_hand(rank_class: int, board: Optional[list[Card]] = None) -> list[Card]:
    """
    Given a rank_class this function will generate a random list of cards from that rank
    class with uniform probability.

    Arguments:
        rank_class (int): The class rank to generate a hand from
        board (Optional[list[Card]]): The board to use
    Returns:
        List[Card]: A uniformly random five-card hand of the given class (two if board is given)
            that forms the given rank class when combined with the board
    Raises:
        ValueError: If it's impossible to generate the given hand
    """
    if board and not 3 <= len(board) <= 5:
        raise ValueError(f"Expected board to be of length 3, 4, or 5. Got {len(board)} instead")

    cards = []
    # straight flush
    if rank_class == 1:
        ranks = generate_straight(board=board)
        suits = generate_flush(board=board)
        cards = [Card(rank + suit) for rank, suit in zip(ranks, suits)]

    # four of a kind
    elif rank_class == 2:
        cards = generate_combo(4, board=board)

    # full house
    elif rank_class == 3:
        cards = generate_combo(3, 2, board=board)

    # flush
    elif rank_class == 4:
        ranks = generate_nonstraight_noncombo(board=board)
        suits = generate_flush(board=board)
        cards = [Card(rank + suit) for rank, suit in zip(ranks, suits)]

    # straight
    elif rank_class == 5:
        ranks = generate_straight(board=board)
        suits = generate_nonflush_suits(board=board)
        cards = [Card(rank + suit) for rank, suit in zip(ranks, suits)]

    # check if higher is possible
    elif board and (is_straight([car.rank for car in board]) or is_flush(board)):
        raise ValueError("Board is a higher class")

    # three of a kind
    if rank_class == 6:
        cards = generate_combo(3, board=board)

    # two pair
    elif rank_class == 7:
        cards = generate_combo(2, 2, board=board)

    # pair
    elif rank_class == 8:
        cards = generate_combo(2, board=board)

    # high card
    elif rank_class == 9:
        ranks = generate_nonstraight_noncombo(board=board)
        suits = generate_nonflush_suits(board=board)
        cards = [Card(rank + suit) for rank, suit in zip(ranks, suits)]

    random.shuffle(cards)
    return cards
