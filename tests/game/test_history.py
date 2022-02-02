from texasholdem.game.action_type import ActionType
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.game import TexasHoldEm


def test_basic_export(tmpdir, call_player):
    """
    Checks if history exists and matches the generated history.

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)

    # mix up chips
    for i in range(len(texas.players)):
        texas.players[i].chips -= i
    old_chips = [player.chips for player in texas.players]

    texas.start_hand()
    while texas.is_hand_running():
        if texas.current_player == 8 and texas.hand_phase == HandPhase.PREFLOP:
            texas.take_action(ActionType.RAISE, 5)
        texas.take_action(*call_player(texas))

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
    with open(history, "r+") as f:
        assert f.read() == texas.hand_history.to_string()


def test_basic_import(tmpdir, call_player):
    """
    Checks if exporting, then importing returns same history

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)

    texas.start_hand()
    while texas.is_hand_running():
        if texas.current_player == 8 and texas.hand_phase == HandPhase.PREFLOP:
            texas.take_action(ActionType.RAISE, 5)
        texas.take_action(*call_player(texas))

    history = tmpdir / "texas.pgn"
    history = texas.export_history(history)

    with open(history, 'r') as f:
        history_string = f.read()

    for state in TexasHoldEm.import_history(history):
        assert history_string.strip().startswith(state.hand_history.to_string().strip())


def test_file_naming(tmpdir, call_player):
    """
    Checks naming conventions of exporting:
        - specifying files and dirs
        - overwriting files
        - renaming files when a dir is specified

    """
    texas = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)

    texas.start_hand()
    while texas.is_hand_running():
        texas.take_action(*call_player(texas))

    # specify file, writes to it
    history = tmpdir / "my_game.pgn"
    texas.export_history(history)
    assert history.exists()

    # specify dir, creates them and makes name texas.pgn
    history = tmpdir / "/pgn/texas_pgns/"
    h1 = texas.export_history(history)
    assert history / "texas.pgn" == h1

    # write again to file no collisions
    h2 = texas.export_history(history)
    assert history / "texas(1).pgn" == h2

    # different game
    texas.start_hand()
    while texas.is_hand_running():
        texas.take_action(*call_player(texas))

    # overwrite
    new_path = history / "texas.pgn"
    new_history = texas.export_history(new_path)

    # overwrite works
    with open(new_history, 'r') as f:
        history_string = f.read()

    last_history = ""
    for state in TexasHoldEm.import_history(new_history):
        last_history = state.hand_history.to_string()
        assert history_string.strip().startswith(last_history.strip())
    assert last_history.strip() == history_string.strip()
