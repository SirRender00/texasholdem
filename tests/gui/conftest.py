# pylint: disable=redefined-outer-name
from unittest.mock import patch, MagicMock

import pytest

from texasholdem.gui.text_gui import TextGUI


_SCREEN_SIZE = (100, 300)


BASIC_GUI_RUNS = 10
COMPLETE_GUI_RUNS = 5


@pytest.fixture(scope='session')
def mock_curses():
    """
    Mocks the enter curses library, replaces the initscr and newwin functions
    to return values from functions in the proper form.
    """
    window_mock = MagicMock()
    window_mock.return_value.getmaxyx.return_value = _SCREEN_SIZE
    window_mock.return_value.getbegyx.return_value = (0, 0)

    with patch('texasholdem.gui.text_gui.curses') as curses:
        curses.initscr = window_mock
        curses.newwin = window_mock
        yield curses


@pytest.fixture()
def input_stdin(mock_curses):
    """
    Use with the mock_curses fixture to accept input from :meth:`curses.getch`
    """

    def inner(string: str):
        ord_string = [ord(c) for c in string]
        mock_curses.initscr.return_value.getch.side_effect = ord_string

    yield inner

    # cleanup, unset
    mock_curses.initscr.return_value.getch.reset_mock(return_value=True, side_effect=True)


@pytest.fixture()
def mock_signal():
    """
    Mock of the signal library for testing purposes
    """
    with patch('texasholdem.gui.text_gui.signal') as signal:
        yield signal


@pytest.fixture()
def text_gui(mock_curses, mock_signal, texas_game):
    # pylint: disable=unused-argument
    """
    Text GUI maker fixture, injects a texas game if not mentioned
    """

    def maker(*args, **kwargs):
        kwargs['game'] = kwargs.get('game', '') or texas_game()
        return TextGUI(*args, **kwargs)

    yield maker
