"""
Config for all tests. Includes:
    - Fixture for a directory path for game history files.
    - Method for stripping comments from a history string.
"""
import os
from typing import Union
from pathlib import Path
import random

import pytest

import tests

from texasholdem.game.game import TexasHoldEm
from texasholdem.game.action_type import ActionType
from texasholdem.game.player_state import PlayerState


GOOD_GAME_HISTORY_DIRECTORY = Path(tests.__file__).parent / "pgns/test_good_pgns"
"""
The path of the directory of the history files with valid game examples
"""

BAD_GAME_HISTORY_DIRECTORY = Path(tests.__file__).parent / "pgns/test_bad_pgns"
"""
The path of the directory of the history files with INVALID game examples
"""

BAD_FORMAT_HISTORY_DIRECTORY = Path(tests.__file__).parent / "pgns/test_bad_format_pgns"
"""
The path of the directory of the history files with INVALID pgns (as opposed to invalid moves)
"""


def pytest_configure(config):
    """ Configure pytest """
    config.addinivalue_line(
        'markers',
        'repeat(n): run the given test function `n` times.')


@pytest.fixture()
def __pytest_repeat_step_number(request):
    """ Internal marker for how many times to repeat a test """
    marker = request.node.get_closest_marker("repeat")
    count = marker and marker.args[0]
    if count > 1:
        return request.param
    return None


@pytest.hookimpl(trylast=True)
def pytest_generate_tests(metafunc):
    """ Generate number of tests corresponding to repeat marker """
    marker = metafunc.definition.get_closest_marker('repeat')
    count = int(marker.args[0]) if marker else 1
    if count > 1:
        metafunc.fixturenames.append("__pytest_repeat_step_number")

        def make_progress_id(curr, total=count):
            return f'{curr + 1}-{total}'

        metafunc.parametrize(
            '__pytest_repeat_step_number',
            range(count),
            indirect=True,
            ids=make_progress_id
        )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # pylint: disable=unused-argument
    """ Used for attaching reports to make available to fixtures """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, 'rep_' + rep.when, rep)


def strip_comments(history_path: Union[str, os.PathLike]) -> str:
    """
    Arguments:
        history_path (Union[str, os.PathLike]): A path to a history pgn
    Returns:
        str: The history string without comments
    """
    with open(history_path, mode='r', encoding='ascii') as file:
        history_string = file.read()

        new_lines = []
        for line in history_string.split('\n'):
            comment_index = line.find('#')

            if comment_index == -1:
                new_lines.append(line)
            elif comment_index != 0:
                new_lines.append(line[:comment_index].strip())

        return '\n'.join(new_lines)


@pytest.fixture()
def texas_game(request):
    """
    Returns:
        Callable[[...], TexasHoldEm]: Create a TexasHoldEm gain. Fills in default
            values if not given buyin=500, big_blind=5, small_blind=2.
    """
    game = None

    def game_maker(*args, **kwargs):
        nonlocal game
        default_kwargs = {'buyin': 500, 'big_blind': 5, 'small_blind': 2}
        default_kwargs.update(kwargs)
        game = TexasHoldEm(*args, **default_kwargs)
        return game

    yield game_maker

    if request.node.rep_call.failed and game and game.hand_history:
        print(game.hand_history.to_string())


@pytest.fixture()
def call_agent():
    """
    A player that calls if another player raised or checks.

    """

    def get_action(game: TexasHoldEm) -> Tuple[ActionType, None]:
        player = game.players[game.current_player]
        if player.state == PlayerState.TO_CALL:
            return ActionType.CALL, None
        return ActionType.CHECK, None

    return get_action


@pytest.fixture()
def random_agent():
    """
    A uniformly random player:
        - If someone raised, CALL, FOLD, or RAISE with uniform probability
        - Else, CHECK, (FOLD if no_fold=False), RAISE with uniform probability
        - If RAISE, the value will be uniformly random in [min_raise, # of chips]

    """

    def get_action(game: TexasHoldEm, no_fold: bool = False) -> Tuple[ActionType, int]:
        bet_amount = game.player_bet_amount(game.current_player)
        chips = game.players[game.current_player].chips
        min_raise = game.value_to_total(game.min_raise(), game.current_player)
        max_raise = bet_amount + chips

        possible = list(ActionType)
        possible.remove(ActionType.ALL_IN)

        # A player did not raise
        if game.players[game.current_player].state == PlayerState.IN:
            possible.remove(ActionType.CALL)
            if no_fold:
                possible.remove(ActionType.FOLD)

        # A player raised
        if game.players[game.current_player].state == PlayerState.TO_CALL:
            possible.remove(ActionType.CHECK)

        # not enough chips to raise
        if max_raise < min_raise:
            possible.remove(ActionType.RAISE)

        action_type, value = random.choice(possible), None
        if action_type == ActionType.RAISE:
            value = random.randint(min_raise, max_raise)

        return action_type, value

    return get_action
