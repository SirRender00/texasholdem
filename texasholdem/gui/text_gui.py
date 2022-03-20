from typing import Iterable, Tuple, Optional

from texasholdem.game.game import TexasHoldEm
from texasholdem.game.player_state import PlayerState
from texasholdem.game.game import HandPhase
from texasholdem.card import card
from texasholdem.game.action_type import ActionType


class TextGUI:
    def __init__(self):
        self.top_spaces = 125
        self.spaces_between = 2
        self.player_ids = []

    def set_player_ids(self, ids: Iterable[int]):
        """
        Sets the player ids to see the cards for.

        Args:
            ids (Iterable[int]): The player ids to see cards for

        """
        self.player_ids = ids

    def _player_state_to_string(self, state):
        if state == PlayerState.SKIP:
            return "SKIP"
        elif state == PlayerState.OUT:
            return "OUT"
        elif state == PlayerState.IN:
            return "IN"
        elif state == PlayerState.TO_CALL:
            return "TO_CALL"
        elif state == PlayerState.ALL_IN:
            return "ALL_IN"

        return "UNKNOWN STATE"

    def _action_to_string(self, action, value):
        if action == ActionType.FOLD:
            return "folds"
        elif action == ActionType.RAISE:
            return "raises to {}".format(value)
        elif action == ActionType.CALL:
            return "calls"
        elif action == ActionType.CHECK:
            return "checks"
        elif action == ActionType.ALL_IN:
            return "goes all in"

    def _get_player_summary(self, poker_game, id):
        card_ids = self.player_ids
        if poker_game.hand_phase == HandPhase.SETTLE:
            card_ids = list(range(poker_game.max_players))

        lines = []

        lines.append("Player {}".format(id))

        if poker_game.btn_loc == id:
            lines.append("Button")
        elif poker_game.sb_loc == id:
            lines.append("Small Blind")
        elif poker_game.bb_loc == id:
            lines.append("Big Blind")

        lines.append("Chips: {}".format(poker_game.players[id].chips))

        status = self._player_state_to_string(poker_game.players[id].state)
        lines.append(status)
        if poker_game.players[id].state == PlayerState.SKIP:
            return lines

        if poker_game.is_hand_running() and id in card_ids:
            cards_int = poker_game.get_hand(id)
            if not cards_int:
                return lines

            cards = card.card_list_to_pretty_str(cards_int)
            lines.append("Cards: {}".format(cards))

        if poker_game.players[id].state == PlayerState.OUT:
            return lines

        bets = sum(poker_game._get_pot(i).get_player_amount(id) for i in range(poker_game.players[id].last_pot + 1))
        lines.append("Bet: {}".format(bets))

        return lines

    def _get_board_summary(self, poker_game):
        lines = []

        pretty_cards = card.card_list_to_pretty_str(poker_game.board)
        lines.append(pretty_cards)

        for i in range(len(poker_game.pots)):
            lines.append("Pot {}: {} ({})".format(i,
                                                  poker_game.pots[i].get_total_amount(),
                                                  poker_game.pots[i].get_amount()))

        return lines

    def accept_input(self) -> Tuple[ActionType, Optional[int]]:
        """
        Accepts input from StdIn and returns the corresponding action tuple.

        Returns:
            Tuple[ActionType, Optional[int]]: The ActionType, value tuple
        """
        args = input("Your Turn!: ")

        if " " in args:
            action_str, val = args.split()
        else:
            action_str, val = args, 0
        action_str = action_str.lower()

        if action_str == "call":
            return ActionType.CALL, None
        elif action_str == "fold":
            return ActionType.FOLD, None
        elif action_str == "all-in":
            return ActionType.ALL_IN, None
        elif action_str == "raise":
            return ActionType.RAISE, float(val)
        elif action_str == "check":
            return ActionType.CHECK, None
        else:
            # always invalid
            return ActionType.RAISE, -1

    def print_action(self, id: int, action: ActionType, val: Optional[int] = None):
        """
        Prints an announcement of the action.

        Args:
            id (int): The player id
            action (ActionType): The action
            val (Optional[int]): The number of chips

        """
        text = "Player {} {}.".format(id, self._action_to_string(action, val))
        print(text)

    def print_state(self, poker_game: TexasHoldEm):
        """
        Prints the state of the given 6 player poker_game. Revealing cards given by
        :meth:`set_player_ids()`

        Args:
            poker_game (TexasHoldEm): The game

        """

        text = ""
        ordering = [[3], [2, 4], ["board"], [1, 5], [0]]

        for lst in ordering:
            n = len(lst)
            if n > 1:
                lines_lst = []
                for elem in lst:
                    lines_lst.append(self._get_player_summary(poker_game, elem))

                max_lines = max([len(x) for x in lines_lst])
                for lines in lines_lst:
                    length = len(lines)
                    for _ in range(0, max_lines - length):
                        lines.append("")

                lines = []
                if len(lines_lst) > 1:
                    for line_tuple in zip(*lines_lst):
                        agg_len = sum(len(line) for line in line_tuple)
                        space_num = self.top_spaces - agg_len
                        space_between = space_num // len(line_tuple)

                        result = ""
                        for j in range(len(line_tuple)):
                            result += line_tuple[j]
                            if j != len(line_tuple) - 1:
                                result += " " * space_between
                        lines.append(result)

            elif lst[0] == "board":
                lines = self._get_board_summary(poker_game)
            else:
                lines = self._get_player_summary(poker_game, lst[0])

            for i in range(len(lines)):
                space_num = (self.top_spaces - len(lines[i])) // 2
                lines[i] = " " * space_num + lines[i]

            for i in range(len(lines)):
                text += lines[i] + "\n"
            text += "\n" * (self.spaces_between - 1)

        print(text)
