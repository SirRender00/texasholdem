"""Tests for the history saving / importing functionality of the TexasHoldEm class.

Includes:
    - Basic exporting
    - Basic importing
    - Importing a file with comments
    - File naming conventions

    - Tests from PGN files that should error because of incorrect format
"""
import glob

import pytest

from texasholdem.game.history import HistoryImportError
from texasholdem.game.action_type import ActionType
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.game import TexasHoldEm

from tests.conftest import strip_comments, BAD_FORMAT_HISTORY_DIRECTORY


def test_basic_export(tmpdir, texas_game, call_agent):
    """
    Checks if history exists and matches the generated history.

    """
    texas = texas_game()

    # mix up chips
    for i, player in enumerate(texas.players, 0):
        player.chips -= i
    old_chips = [player.chips for player in texas.players]

    texas.start_hand()
    while texas.is_hand_running():
        if texas.current_player == 8 and texas.hand_phase == HandPhase.PREFLOP:
            texas.take_action(ActionType.RAISE, total=texas.big_blind + 5)
        texas.take_action(*call_agent(texas))

    assert all((texas.hand_history.prehand,
               texas.hand_history.preflop,
               texas.hand_history.flop,
               texas.hand_history.turn,
               texas.hand_history.river,
               texas.hand_history.settle))

    assert texas.hand_history.prehand.btn_loc == texas.btn_loc
    assert texas.hand_history.prehand.small_blind == texas.small_blind
    assert texas.hand_history.prehand.big_blind == texas.big_blind
    assert all(old_chips[i] == texas.hand_history.prehand.player_chips[i]
               for i in range(len(texas.players)))

    history = tmpdir / "texas.pgn"
    history = texas.export_history(history)
    with open(history, 'r', encoding="ascii") as file:
        assert file.read() == texas.hand_history.to_string()


def test_basic_import(tmpdir, texas_game, call_agent):
    """
    Checks if exporting, then importing returns same history

    """
    texas = texas_game()
    texas.start_hand()
    while texas.is_hand_running():
        if texas.current_player == 8 and texas.hand_phase == HandPhase.PREFLOP:
            texas.take_action(ActionType.RAISE, total=texas.big_blind + 5)
        texas.take_action(*call_agent(texas))

    history = tmpdir / "texas.pgn"
    history = texas.export_history(history)

    with open(history, 'r', encoding="ascii") as file:
        history_string = file.read()

    for state in TexasHoldEm.import_history(history):
        assert history_string.strip().startswith(state.hand_history.to_string().strip())


def test_import_comments(history_file_with_comments):
    """
    Checks if importing a history file with comments is okay
    """
    history_string = strip_comments(history_file_with_comments)

    for state in TexasHoldEm.import_history(history_file_with_comments):
        assert history_string.strip().startswith(state.hand_history.to_string().strip())


def test_file_naming(tmpdir, texas_game, call_agent):
    """
    Checks naming conventions of exporting:
        - specifying files and dirs
        - overwriting files
        - renaming files when a dir is specified

    """
    texas = texas_game()
    texas.start_hand()
    while texas.is_hand_running():
        texas.take_action(*call_agent(texas))

    # specify file, writes to it
    history = tmpdir / "my_game.pgn"
    texas.export_history(history)
    assert history.exists()

    # specify dir, creates them and makes name texas.pgn
    history = tmpdir / "/pgn/texas_pgns/"
    history1 = texas.export_history(history)
    assert history / "texas.pgn" == history1

    # write again to file no collisions
    history2 = texas.export_history(history)
    assert history / "texas(1).pgn" == history2

    # write again to file no collisions
    history3 = texas.export_history(history)
    assert history / "texas(2).pgn" == history3

    # different game
    texas.start_hand()
    while texas.is_hand_running():
        texas.take_action(*call_agent(texas))

    # overwrite
    new_path = history / "texas.pgn"
    new_history = texas.export_history(new_path)

    # overwrite works
    with open(new_history, 'r', encoding="ascii") as file:
        history_string = file.read()

    last_history = ""
    for state in TexasHoldEm.import_history(new_history):
        last_history = state.hand_history.to_string()
        assert history_string.strip().startswith(last_history.strip())
    assert last_history.strip() == history_string.strip()


@pytest.mark.parametrize("pgn", glob.glob(str(BAD_FORMAT_HISTORY_DIRECTORY / '*'),
                                          recursive=True))
def test_bad_format_history(pgn):
    """
    Tries to import the given bad format files and ensures it errors.
    """
    with pytest.raises(HistoryImportError):
        for _ in TexasHoldEm.import_history(pgn):
            pass
