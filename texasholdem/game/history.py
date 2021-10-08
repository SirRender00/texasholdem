"""The history module includes various dataclasses intended
to keep the history of the game to be able to replay hands and
export/import notation of the game.

Texas Hold Em Notation Conventions:
    - The button is assigned ID 0

"""

from __future__ import annotations
from typing import Optional, Tuple, Union
from dataclasses import dataclass

from texasholdem.game.action_type import ActionType
from texasholdem.card.card import Card
from texasholdem.game.hand_phase import HandPhase


FILE_EXTENSION = 'pgn'


@dataclass()
class PrehandHistory:
    """Prehand history class, button location, and
    the player chip counts."""
    btn_loc: int
    big_blind: int
    small_blind: int
    player_chips: dict[int, int]
    player_cards: dict[int, list[Card]]

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
        """
        big_blind, small_blind, chips_str, cards_str = string.split('\n')
        _, big_blind = big_blind.split(': ')
        _, small_blind = small_blind.split(': ')

        _, chips_str = chips_str.split(': ')
        player_chips = [int(chip_str) for chip_str in chips_str.split(',')]
        num_players = len(player_chips)

        _, cards_str = cards_str.split(': ')
        cards_data = cards_str.split(',')
        cards_data = [card_data.strip('[').strip(']').split(' ') for card_data in cards_data]
        player_cards = [[Card(c1), Card(c2)] for c1, c2 in cards_data]

        return PrehandHistory(0,
                              int(big_blind),
                              int(small_blind),
                              dict(zip(range(num_players), player_chips)),
                              dict(zip(range(num_players), player_cards)))


@dataclass()
class PlayerAction:
    """PlayerAction history class, includes the player id, the action type,
    and the value."""
    player_id: int
    action_type: ActionType
    value: Optional[int]

    def to_string(self, canon_ids: dict[int, int]) -> str:
        """
        Arguments:
            canon_ids (dict[int, int]): Map of old_id -> new_id where the new btn_loc is 0
        Returns:
            str: The string representation of a player action: id, action, amount
        """
        string = f"({canon_ids[self.player_id]},{self.action_type.name}"
        if self.value is not None and self.value > 0:
            string += "," + str(self.value)
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
        string = string.strip().strip("(").strip(")")
        data = string.split(",")
        player_id, action_type = int(data[0]), ActionType[data[1]]
        value = None if len(data) <= 2 else int(data[2])
        return PlayerAction(player_id, action_type, value)


@dataclass()
class BettingRoundHistory:
    """BettingRound history class, includes new cards and
    a list of PlayerActions."""
    new_cards: list[Card]
    actions: list[PlayerAction]

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
        for action_line in data:
            _, action_line = action_line.split(". ")
            action_str += action_line

        actions = [PlayerAction.from_string(string) for string in action_str.split(";")]

        return BettingRoundHistory(new_cards, actions)


@dataclass()
class SettleHistory:
    """Settle history class, includes new cards and
    a dictionary of winners: player_id -> (rank, amount won)"""
    new_cards: list[Card]
    winners: dict[int, Tuple[int, int]]

    def to_string(self, canon_ids: dict[int, int]) -> str:
        """
        Arguments:
            canon_ids (dict[int, int]): Map of old_id -> new_id where the new btn_loc is 0
        Returns:
            str: The string representation of the settle history: new cards revealed,
                winners (id, hand rank, amount)
        """
        winner_strs = [f'{canon_ids[winner], rank, amount}'
                       for winner, (rank, amount) in self.winners.items()]
        return f"New Cards: [{','.join(str(card) for card in self.new_cards)}]\n" \
               f"Winners: {';'.join(winner_strs)}"

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
        winners_data = [winner_str.strip('(').strip(')').split(',')
                        for winner_str in winners_str.split(';')]
        winners = {int(i): (int(rank), int(amount)) for i, rank, amount in winners_data}
        return SettleHistory(new_cards, winners)


@dataclass()
class History:
    """History class of a hand of TexasHoldEm. Includes one history item for each HandPhase.
    In total, this constitutes a minimal amount of information necessary to replay a hand.

    This class also includes to_string() and from_string() methods which provides ways to
    write / read human-readable information to / from files.
    """
    prehand: PrehandHistory = None
    preflop: BettingRoundHistory = None
    settle: SettleHistory = None
    flop: Optional[BettingRoundHistory] = None
    turn: Optional[BettingRoundHistory] = None
    river: Optional[BettingRoundHistory] = None

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
    def from_string(string: str) -> History:
        """
        Reverse of to_string()

        Arguments:
            string (str): The string as returned from to_string()
        Returns:
            History: The hand history as represented by the string
        """
        history = History()
        sections = string.split('\n\n')
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
                raise ValueError(f"Unexpected header in history: '{header}'")

            history_item = history_item.from_string(rest)
            history[HandPhase[header]] = history_item

        return history

    def __setitem__(self, hand_phase: HandPhase,
                    history: Union[PrehandHistory, BettingRoundHistory, SettleHistory]) -> None:
        setattr(self, hand_phase.name.lower(), history)

    def __getitem__(self, hand_phase: HandPhase) -> \
            Union[PrehandHistory, BettingRoundHistory, SettleHistory]:
        return getattr(self, hand_phase.name.lower())
