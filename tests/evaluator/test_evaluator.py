"""Tests for the evaluator module

Includes:
    - Fuzz testing for
        - 5 v 5 unrelated hands
        - 2 cards with board length 3, 4, 5
        - evaluator module convenience methods
            - get_rank_class
            - rank_to_string
            - five_card_percentage
"""
import itertools
import math
import random

import pytest

from texasholdem.evaluator import evaluator
from tests.evaluator.conftest import (
    generate_sample_hand,
    less_hands_same_class,
    FUZZ_COMPARE_WITH_BOARD,
    GETTER_CONVENIENCE_RUNS,
    MAX_HAND_RANK,
)


@pytest.mark.repeat(FUZZ_COMPARE_WITH_BOARD)
@pytest.mark.parametrize("board_len", (0, 3, 4, 5))
def test_fuzz_compare_with_board(board_len):
    """
    Tests if evaluate returns proper comparisons for two random hands, each with
    two or five cards behind and sharing zero, three, four, or five cards on the board.
    """
    class_choices = list(evaluator.LOOKUP_TABLE.RANK_CLASS_TO_STRING.keys())
    class1, class2 = random.choices(class_choices, k=2)

    board = [] if board_len == 0 else generate_sample_hand(class1)[:board_len]

    hand1 = generate_sample_hand(class1, board=board)

    hand2 = None
    while not hand2:
        try:
            hand2 = generate_sample_hand(class2, board=board)
        except ValueError:
            class_choices.remove(class2)
            class2 = random.choice(class_choices)

    score1, score2 = evaluator.evaluate(hand1, board), evaluator.evaluate(hand2, board)

    hand1 = list(
        min(
            itertools.combinations(board + hand1, 5),
            key=lambda hand: evaluator.evaluate([], list(hand)),
        )
    )
    hand2 = list(
        min(
            itertools.combinations(board + hand2, 5),
            key=lambda hand: evaluator.evaluate([], list(hand)),
        )
    )

    if class1 > class2:
        assert score1 > score2, f"Expected {hand2} to be better than {hand1}"
    elif class1 < class2:
        assert score1 < score2, f"Expected {hand1} to be better than {hand2}"
    elif less_hands_same_class(class1, hand1, hand2):
        assert score1 > score2, f"Expected {hand2} to be better than {hand1}"
    elif less_hands_same_class(class1, hand2, hand1):
        assert score1 < score2, f"Expected {hand1} to be better than {hand2}"
    else:
        assert score1 == score2, f"Expected {hand1} and {hand2} to have the same score"


@pytest.mark.repeat(GETTER_CONVENIENCE_RUNS)
def test_get_rank_class():
    """
    Tests if get_rank_class() returns the correct rank class
    """
    class1 = random.choice(list(evaluator.LOOKUP_TABLE.RANK_CLASS_TO_STRING.keys()))
    hand = generate_sample_hand(class1)
    score = evaluator.evaluate([], hand)
    assert evaluator.get_rank_class(score) == class1


@pytest.mark.repeat(GETTER_CONVENIENCE_RUNS)
def test_rank_to_string():
    """
    Tests if rank_to_string() returns the correct string
    """
    class1 = random.choice(list(evaluator.LOOKUP_TABLE.RANK_CLASS_TO_STRING.keys()))
    hand = generate_sample_hand(class1)
    score = evaluator.evaluate([], hand)
    assert (
        evaluator.rank_to_string(score)
        == evaluator.LOOKUP_TABLE.RANK_CLASS_TO_STRING[class1]
    )


@pytest.mark.repeat(GETTER_CONVENIENCE_RUNS)
def test_five_card_percentage():
    """
    Tests if get_five_card_rank_percentage() returns the correct percentage
    """
    class1 = random.choice(list(evaluator.LOOKUP_TABLE.RANK_CLASS_TO_STRING.keys()))
    hand = generate_sample_hand(class1)
    score = evaluator.evaluate([], hand)
    assert math.isclose(
        evaluator.get_five_card_rank_percentage(score),
        1 - float(score) / float(MAX_HAND_RANK),
    )
