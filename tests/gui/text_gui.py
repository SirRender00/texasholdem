# pylint: disable=protected-access
from importlib.metadata import version
import itertools

import pytest

from texasholdem.card import card
from texasholdem.game.action_type import ActionType
from texasholdem.gui.text_gui import TextGUI

from tests.gui.conftest import BASIC_GUI_RUNS, COMPLETE_GUI_RUNS


def assert_content_in_block(gui: TextGUI, block_name: str, content: str):
    """
    Asserts that the given content string is set in the content field of the
    given block.
    """
    block = gui.main_block.get_block(block_name)
    _, kwargs = block.content
    assert content in "".join(kwargs["content"])


def assert_content_not_in_block(gui: TextGUI, block_name: str, content: str):
    """
    Asserts that the given content string is NOT set in the content field of the
    given block.
    """
    block = gui.main_block.get_block(block_name)
    _, kwargs = block.content
    assert content not in "".join(kwargs["content"])


def display_checks(game, gui):
    """
    Checks if the Text GUI has the proper states set in their blocks
    """
    for player in game.players:
        assert_content_in_block(
            gui, f"PLAYER_INFO_{player.player_id}", f"Player {player.player_id}"
        )
        assert_content_in_block(
            gui, f"PLAYER_INFO_{player.player_id}", player.state.name
        )
        assert_content_in_block(
            gui, f"PLAYER_INFO_{player.player_id}", str(player.chips)
        )

        if player.player_id in gui.visible_players:
            assert_content_in_block(
                gui,
                f"PLAYER_INFO_{player.player_id}",
                card.card_list_to_pretty_str(game.get_hand(player.player_id)),
            )
        else:
            assert_content_not_in_block(
                gui,
                f"PLAYER_INFO_{player.player_id}",
                card.card_list_to_pretty_str(game.get_hand(player.player_id)),
            )

        assert_content_in_block(
            gui,
            f"PLAYER_CHIPS_{player.player_id}",
            str(game.player_bet_amount(player.player_id)),
        )

    assert_content_in_block(gui, "BOARD", card.card_list_to_pretty_str(game.board))

    # History block depends on size, so just default to
    # Checking the history block is set
    block = gui.main_block.get_block("HISTORY")
    _, kwargs = block.content
    assert gui._history_block() == kwargs["content"]

    assert_content_in_block(gui, "VERSION", version("texasholdem"))


def test_import():
    # pylint: disable=import-outside-toplevel,unused-import
    """
    Tests import curses module (useful for checking Windows compatibility)
    """
    import _curses
    import curses


@pytest.mark.repeat(COMPLETE_GUI_RUNS)
def test_display_state(text_gui, random_agent):
    """
    Tests display of a state
    """
    gui = text_gui()

    while gui.game.is_game_running():
        gui.game.start_hand()

        while gui.game.is_hand_running():
            gui.game.take_action(*random_agent(gui.game))
            gui.display_state()
            display_checks(gui.game, gui)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("raise to 50\n", (ActionType.RAISE, 50)),
        ("raise 50\n", (ActionType.RAISE, 50)),
        ("call\n", (ActionType.CALL, None)),
        ("fold\n", (ActionType.FOLD, None)),
        ("check\n", (ActionType.CHECK, None)),
        ("\t raise to 50   \n", (ActionType.RAISE, 50)),
    ],
)
def test_input(text, expected, text_gui, input_stdin):
    """
    Test the input functionality from the command line
    """
    gui = text_gui()
    input_stdin(text)
    assert expected == gui.accept_input()


def test_visible_players(text_gui):
    """
    Tests the visible players functionality
    """
    gui = text_gui()
    gui.game.start_hand()

    for length in range(1, gui.game.max_players + 1):
        for visible_players in itertools.combinations(
            range(gui.game.max_players), length
        ):
            gui.set_visible_players(visible_players)
            gui.display_state()

            for player_id in range(gui.game.max_players):
                if player_id in gui.visible_players:
                    assert_content_in_block(
                        gui,
                        f"PLAYER_INFO_{player_id}",
                        card.card_list_to_pretty_str(gui.game.get_hand(player_id)),
                    )
                else:
                    assert_content_not_in_block(
                        gui,
                        f"PLAYER_INFO_{player_id}",
                        card.card_list_to_pretty_str(gui.game.get_hand(player_id)),
                    )


@pytest.mark.repeat(BASIC_GUI_RUNS)
def test_visible_players_settle(text_gui, random_agent):
    """
    Tests the visible players functionality in the settle phase is set correctly.
    """
    gui = text_gui(visible_players=())
    gui.game.start_hand()

    while gui.game.is_hand_running():
        gui.game.take_action(*random_agent(gui.game))

    # settle
    gui.display_win()
    for player_id in range(gui.game.max_players):
        in_pot = list(gui.game.in_pot_iter())
        if len(in_pot) > 1 and player_id in in_pot:
            assert_content_in_block(
                gui,
                f"PLAYER_INFO_{player_id}",
                card.card_list_to_pretty_str(gui.game.get_hand(player_id)),
            )
        else:
            assert_content_not_in_block(
                gui,
                f"PLAYER_INFO_{player_id}",
                card.card_list_to_pretty_str(gui.game.get_hand(player_id)),
            )
