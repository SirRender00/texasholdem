"""The history module includes various dataclasses intended
to keep the history of the game to be able to replay hands and
export/import notation of the game.

Texas Hold Em Notation Conventions:

    - The button is assigned ID 0
    - Each action is a tuple :code:`(player_id, action_type, total)`
    - The winner section is a per-pot tuple :code:`(Pot id, amount, best rank, winner ids)`

"""
from __future__ import annotations
from typing import Optional, Union, Tuple
from dataclasses import dataclass
from pathlib import Path
import os

from texasholdem.game.action_type import ActionType
from texasholdem.card.card import Card
from texasholdem.game.hand_phase import HandPhase


FILE_EXTENSION = 'pgn'
"""
The extension for the game notation file.

"""


class HistoryImportError(Exception):
    """
    The history classes will throw this error if it cannot import the given PGN file.

    """


@dataclass()
class PrehandHistory:
    """
    History of the Prehand Phase

    """
    btn_loc: int
    """
    The id of the player with the button
    """
    big_blind: int
    """
    The id of the player with the big blind
    """
    small_blind: int
    """
    The id of the player with the small blind
    """
    player_chips: dict[int, int]
    """
    The number of chips for each player
    """
    player_cards: dict[int, list[Card]]
    """
    The cards for each player
    """

    def to_string(self, canon_ids: dict[int, int]) -> str:
        """
        Arguments:
            canon_ids (dict[int, int]): Map of old_id -> new_id where the new btn_loc is 0
        Returns:
            str: The string representation of the prehand history: blind sizes, chips, and cards

        """
        str_player_cards = {i: [str(card) for card in self.player_cards[i]] for i in canon_ids}

        return f"Big Blind: {self.big_blind}\n" \
               f"Small Blind: {self.small_blind}\n" \
               f"Player Chips: {','.join(str(self.player_chips[i]) for i in canon_ids)}\n" \
               f"Player Cards: " \
               f"{','.join(['[' + ' '.join(str_player_cards[i]) + ']' for i in canon_ids])}"

    @staticmethod
    def from_string(string: str) -> PrehandHistory:
        """
        Reverse of to_string()

        Arguments:
            string (str): The string as returned from to_string()
        Returns:
            PrehandHistory: The prehand history as represented by the string
        Raises:
            HistoryImportError: If missing information or a mismatch between cards and chips

        """
        big_blind, small_blind, chips_str, cards_str = string.split('\n')
        _, big_blind = big_blind.split(': ')
        _, small_blind = small_blind.split(': ')

        _, chips_str = chips_str.split(': ')
        player_chips = [int(chip_str) for chip_str in chips_str.split(',')]
        num_players = len(player_chips)

        _, cards_str = cards_str.split(': ')
        cards_data = cards_str.split(',')
        cards_data = [card_data.strip('[]').split(' ') for card_data in cards_data]
        player_cards = [[Card(c1), Card(c2)] for c1, c2 in cards_data]

        if len(player_chips) != len(player_cards):
            raise HistoryImportError(f"Mismatch number of player chips ({len(player_chips)}) "
                                     f"and player cards ({len(player_cards)})")

        return PrehandHistory(0,
                              int(big_blind),
                              int(small_blind),
                              dict(zip(range(num_players), player_chips)),
                              dict(zip(range(num_players), player_cards)))


@dataclass()
class PlayerAction:
    """
    History of a Player Action

    """
    player_id: int
    """
    The player id
    """
    action_type: ActionType
    """
    The action type
    """
    total: Optional[int] = None
    """
    The total raise amount
    """
    value: Optional[int] = None
    """
    The amount raised
    """

    def to_string(self, canon_ids: dict[int, int]) -> str:
        """
        Arguments:
            canon_ids (dict[int, int]): Map of old_id -> new_id where the new btn_loc is 0
        Returns:
            str: The string representation of a player action: id, action, amount
        """
        string = f"({canon_ids[self.player_id]},{self.action_type.name}"
        if self.total is not None and self.total > 0:
            string += "," + str(self.total)
        string += ")"

        return string

    @staticmethod
    def from_string(string: str) -> PlayerAction:
        """
        Reverse of to_string()

        Arguments:
            string (str): The string as returned from to_string()
        Returns:
            PlayerAction: The player action as represented by the string
        """
        string = string.strip().strip('()')
        data = string.split(",")
        player_id, action_type = int(data[0]), ActionType[data[1]]
        total = None if len(data) <= 2 else int(data[2])
        return PlayerAction(player_id=player_id, action_type=action_type, total=total)


@dataclass()
class BettingRoundHistory:
    """
    History of a Betting Round

    """
    new_cards: list[Card]
    """
    The new cards that were added this round
    """
    actions: list[PlayerAction]
    """
    A list of PlayerActions
    """

    def to_string(self, canon_ids: dict[int, int]) -> str:
        """
        Arguments:
            canon_ids (dict[int, int]): Map of old_id -> new_id where the new btn_loc is 0
        Returns:
            str: The string representation of the betting round history:
                new cards revealed, ordered list of actions
        """
        new_cards = f"New Cards: [{','.join(str(card) for card in self.new_cards)}]"
        counts = {}
        orbits = {}

        for action in self.actions:
            counts[action.player_id] = counts.get(action.player_id, 0) + 1
            min_count = max(counts.values())

            if min_count not in orbits:
                orbits[min_count] = []
            orbits[min_count].append(action.to_string(canon_ids))

        orbit_lines = [f"{orbit_num}. " +
                       ";".join(orbit_line) for orbit_num, orbit_line in orbits.items()]
        action_str = "\n".join(orbit_lines)
        return new_cards + "\n" + action_str

    @staticmethod
    def from_string(string: str) -> BettingRoundHistory:
        """
        Reverse of to_string()

        Arguments:
            string (str): The string as returned from to_string()
        Returns:
            BettingRoundHistory: The betting round as represented by the string
        """
        data = string.split('\n')
        card_str, data = data[0], data[1:]
        _, card_str = card_str.split('[')
        card_str, _ = card_str.split(']')

        if card_str:
            new_cards = [Card(string) for string in card_str.split(',')]
        else:
            new_cards = []

        action_str = ""
        for i, action_line in enumerate(data, 1):
            _, action_line = action_line.split(". ")
            action_str += action_line
            if i != len(data):
                action_str += ';'

        actions = [PlayerAction.from_string(string) for string in action_str.split(";")]

        return BettingRoundHistory(new_cards, actions)


@dataclass()
class SettleHistory:
    """
    History of the Settle Phase

    """
    new_cards: list[Card]
    """
    The new cards that were added this round
    """
    pot_winners: dict[int, Tuple[int, int, list[int]]]
    """
    A map from pot_id to a tuple of winner data :code:`amount, best rank, list of winners`
    """

    def to_string(self, canon_ids: dict[int, int]) -> str:
        """
        Arguments:
            canon_ids (dict[int, int]): Map of old_id -> new_id where the new btn_loc is 0
        Returns:
            str: The string representation of the settle history: new cards revealed,
                and the winners per pot: (pot_id, total_amount, best_rank, winners list)
        """
        pot_lists = []
        for pot_id, (amount, best_rank, winners_list) in self.pot_winners.items():
            pot_lists.append((pot_id, amount, best_rank, [canon_ids[winner]
                                                          for winner in winners_list]))
        pot_strs = [f'(Pot {pot_id},{amount},{best_rank},{str(winners_list)})'
                    for pot_id, amount, best_rank, winners_list in pot_lists]
        return f"New Cards: [{','.join(str(card) for card in self.new_cards)}]\n" \
               f"Winners: {';'.join(pot_strs)}"

    @staticmethod
    def from_string(string: str) -> SettleHistory:
        """
        Reverse of to_string()

        Arguments:
            string (str): The string as returned from to_string()
        Returns:
            SettleHistory: The settle history as represented by the string
        """
        cards_str, winners_str = string.split('\n')
        _, cards_str = cards_str.split('[')
        cards_str, _ = cards_str.split(']')

        if cards_str:
            new_cards = [Card(string) for string in cards_str.split(',')]
        else:
            new_cards = []

        _, winners_str = winners_str.split(': ')
        pot_winners_data = [winner_str.strip('()')
                            .replace(' ', '')
                            .replace('[', '')
                            .replace(']', '')
                            .split(',')
                            for winner_str in winners_str.split(';')]
        pot_winners_data = [(data[0], data[1], data[2], data[3:])
                            for data in pot_winners_data]
        pot_winners = {int(pot_name[(pot_name.find('Pot') + 3):]):
                       (int(amount), int(best_rank), [int(winner) for winner in winners_list])
                       for pot_name, amount, best_rank, winners_list in pot_winners_data}
        return SettleHistory(new_cards, pot_winners)


@dataclass()
class History:
    """
    History class of a hand of TexasHoldEm. Includes one history item for each HandPhase.
    In total, this constitutes a minimal amount of information necessary to replay a hand.

    This class also includes :meth:`to_string()` and :meth:`from_string()` methods which
    provides ways to write / read human-readable information to / from files.

    """
    prehand: PrehandHistory = None
    """
    The Prehand History
    """
    preflop: BettingRoundHistory = None
    """
    The Preflop History
    """
    settle: SettleHistory = None
    """
    The Settle History
    """
    flop: Optional[BettingRoundHistory] = None
    """
    The Flop History
    """
    turn: Optional[BettingRoundHistory] = None
    """
    The Turn History
    """
    river: Optional[BettingRoundHistory] = None
    """
    The River History
    """

    def to_string(self) -> str:
        """
        Returns the string representation of the hand history, including the blind sizes,
        chips, players cards, in addition to revealed cards per street and an ordered list
        of actions per street. By convention, we assign the button an ID of 0 in this
        representation.

        Returns:
            str: The string representation of the hand history.

        """
        num_players = len(self.prehand.player_chips)
        old_ids = [i % num_players
                   for i in range(self.prehand.btn_loc, self.prehand.btn_loc + num_players)
                   if self.prehand.player_chips[i % num_players] > 0]
        canon_ids = dict(zip(old_ids, range(len(old_ids))))

        string = ""

        for history_item, name in [(self.prehand, HandPhase.PREHAND.name),
                                   (self.preflop, HandPhase.PREFLOP.name),
                                   (self.flop, HandPhase.FLOP.name),
                                   (self.turn, HandPhase.TURN.name),
                                   (self.river, HandPhase.RIVER.name),
                                   (self.settle, HandPhase.SETTLE.name)]:
            if history_item is not None:
                string += f"{name.upper()}\n" + history_item.to_string(canon_ids)
                string += '\n' if name == HandPhase.SETTLE.name else '\n\n'

        return string

    @staticmethod
    def _strip_comments(string: str) -> str:
        """
        Arguments:
            string (str): A history string
        Returns:
            str: The history string without comments.

        """
        new_lines = []
        for line in string.split('\n'):
            comment_index = line.find('#')

            if comment_index == -1:
                new_lines.append(line)
            elif comment_index != 0:
                new_lines.append(line[:comment_index].strip())

        return '\n'.join(new_lines)

    @staticmethod
    def from_string(string: str) -> History:
        """
        Reverse of :meth:`to_string()`

        Arguments:
            string (str): The string as returned from :meth:`to_string()`
        Returns:
            History: The hand history as represented by the string
        Raises:
            HistoryImportError: If the PGN file is invalid

        """
        history = History()
        sections = History._strip_comments(string).split('\n\n')

        for section in sections:
            newline = section.find('\n')
            header, rest = section[:newline], section[(newline+1):]
            if header == HandPhase.PREHAND.name:
                history_item = PrehandHistory
            elif header in (HandPhase.PREFLOP.name,
                            HandPhase.FLOP.name,
                            HandPhase.TURN.name,
                            HandPhase.RIVER.name):
                history_item = BettingRoundHistory
            elif header == HandPhase.SETTLE.name:
                # remove trailing newline for end of line
                history_item, rest = SettleHistory, rest[:-1]
            else:
                raise HistoryImportError(f"Unexpected header in history: '{header}'")

            history_item = history_item.from_string(rest)
            history[HandPhase[header]] = history_item

        return history

    def export_history(self, path: Union[str, os.PathLike] = "./texas.pgn") -> os.PathLike:
        """
        Exports the hand history to a human-readable file. If a directory is given,
        finds a name of the form :code:`texas(n).pgn` to export to. PGN files can consequently
        be imported with :meth:`import_history()`.

        Arguments:
            path (str | os.PathLike]): The directory or file to export the history to, defaults
                to the current working directory at the file `./texas.pgn`
        Returns:
            os.PathLike: The path to the history file

        """
        path_or_dir = Path(path)
        hist_path = path_or_dir

        if not hist_path.suffixes:
            hist_path.mkdir(parents=True, exist_ok=True)
            hist_path = hist_path / f"texas.{FILE_EXTENSION}"

        if f".{FILE_EXTENSION}" not in hist_path.suffixes:
            hist_path = hist_path.parent / f"{hist_path.name}.{FILE_EXTENSION}"

        # resolve lowest file_num
        original_path = hist_path
        num = 1
        while hist_path.exists():
            hist_path = original_path.parent / f"{original_path.stem}({num}).{FILE_EXTENSION}"
            num += 1

        with open(hist_path, mode="w+", encoding="ascii") as file:
            file.write(self.to_string())

        return hist_path.absolute().resolve()

    @staticmethod
    def import_history(path: Union[str, os.PathLike]) -> History:
        """
        Import a PGN file i.e. as exported from :meth:`export_history()`. Returns an
        iterator over game states as specified from the history.

        Arguments:
            path (str | os.PathLike): The PGN file to import from
        Returns:
            History: The history object represented by the PGN file
        Raises:
            HistoryImportError: If the file given does not exist or if the file is invalid

        """
        # pylint: disable=protected-access
        path = Path(path)
        if not path.exists():
            raise HistoryImportError(f'File not found: {path.absolute()}')

        # reconstitute history
        with open(path, mode='r', encoding='ascii') as file:
            try:
                history = History.from_string(file.read())
            except ValueError as err:
                raise HistoryImportError() from err

        # run checks
        history._check_missing_sections()
        history._check_unique_cards()
        history._check_correct_board_len()

        if len(history.prehand.player_chips) <= 1:
            raise HistoryImportError(f"Expected at least 2 players in this game, "
                                     f"got {len(history.prehand.player_chips)}")

        return history

    def _check_missing_sections(self):
        """
        Raises:
            HistoryImportError: If there is a section missing

        """
        if not self.preflop:
            raise HistoryImportError("Preflop section is missing")
        if not self.settle:
            raise HistoryImportError("Settle section is missing")

        for hand_phase in (HandPhase.PREFLOP,
                           HandPhase.FLOP,
                           HandPhase.TURN):
            if self[hand_phase.next_phase()] and not self[hand_phase]:
                raise HistoryImportError(f"Found a section for {hand_phase.next_phase().name} "
                                         f"but not a section for {hand_phase.name}")

    def _check_unique_cards(self):
        """
        Raises:
            HistoryImportError: If the cards in the history are not unique

        """
        cards = sum(self.prehand.player_cards.values(), [])
        for hand_phase in (HandPhase.PREFLOP,
                           HandPhase.FLOP,
                           HandPhase.TURN,
                           HandPhase.RIVER):
            history_item = self[hand_phase]
            if history_item:
                cards += history_item.new_cards

        if len(cards) != len(set(cards)):
            raise HistoryImportError("Expected cards given in history to be unique.")

    def _check_correct_board_len(self):
        """
        Raises:
            HistoryImportError: If the cards do not come out in the proper amount

        """
        total_board_len = 0
        for hand_phase in (HandPhase.PREFLOP,
                           HandPhase.FLOP,
                           HandPhase.TURN,
                           HandPhase.RIVER):
            history_item = self[hand_phase]
            if history_item:
                if len(history_item.new_cards) != hand_phase.new_cards():
                    raise HistoryImportError(f"Expected {hand_phase.new_cards()} "
                                             f"new cards in phase {hand_phase.name}")
                total_board_len += len(history_item.new_cards)

        # settle
        for _, (_, rank, _) in self.settle.pot_winners.items():
            if rank != -1:
                if len(self.settle.new_cards) != 5 - total_board_len:
                    raise HistoryImportError(f"Expected {5 - total_board_len} "
                                             f"to come out during settle phase")

    def __setitem__(self, hand_phase: HandPhase,
                    history: Union[PrehandHistory, BettingRoundHistory, SettleHistory]) -> None:
        setattr(self, hand_phase.name.lower(), history)

    def __getitem__(self, hand_phase: HandPhase) -> \
            Union[PrehandHistory, BettingRoundHistory, SettleHistory]:
        return getattr(self, hand_phase.name.lower())
