"""
The game module includes lightweight data classes:
    - Player
        - The player class keeps track of the chips, player_state,
          last_pot, and player_id of the player.
    - Pot
        - The pot class represents a betting pot which players
          can post to. Includes helper functions and attributes that deal
          with split pots or how much a player needs to call.

It also includes the main TexasHoldEm class of the texasholdem package.
"""
from __future__ import annotations

import os
from typing import Iterator, Callable, Dict, Tuple, Optional, Union, List
from enum import Enum, auto
import random

from texasholdem.card.card import Card
from texasholdem.card.deck import Deck
from texasholdem.game.history import (History, PrehandHistory,
                                      BettingRoundHistory, PlayerAction,
                                      HistoryImportError, SettleHistory)
from texasholdem.game.action_type import ActionType
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.player_state import PlayerState
from texasholdem.evaluator import evaluator


class Player:
    # pylint: disable=too-few-public-methods
    """
    The TexasHoldEm object uses this Player as a bookkeeping mechanism for:
        - Chip count
        - PlayerState
        - Which pots the player is in
    """

    def __init__(self, player_id, chips):
        self.player_id = player_id
        self.chips = chips
        self.state = PlayerState.IN

        # invariant: last_pot is the newest pot that player is eligible for
        self.last_pot = 0


class Pot:
    """
    Class representing a betting pot, players will post to the pot.
    If players post more than the raised amount, we set the new raised amount.

    At the end of a betting round, the bets are consolidated and reset.
    """

    def __init__(self):
        self.amount = 0
        self.raised = 0
        self.player_amounts = {}

    def chips_to_call(self, player_id: int) -> int:
        """Returns the amount of chips to call for the given player.

        Args:
            player_id (int): The player_id of the player in the pot
        Returns:
            int: The amount the player needs to call to be in this pot
              (this is just self.raised if the player hasn't bet yet)

        """
        return self.raised - self.player_amounts.get(player_id, 0)

    def player_post(self, player_id: int, amount: int):
        """The given player posts amount into this pot. If player[player_id].amount > raised,
        sets new raised value.

        Arguments:
            player_id (int): The player_id of the player posting
            amount (int): The amount to post into this pot

        """
        self.player_amounts[player_id] = self.player_amounts.get(player_id, 0) + amount

        if self.player_amounts[player_id] > self.raised:
            self.raised = self.player_amounts[player_id]

    def get_player_amount(self, player_id: int) -> int:
        """
        Arguments:
            player_id (int): Player player_id
        Returns:
            int: the amount the player has bet currently for this pot.

        """
        return self.player_amounts.get(player_id, 0)

    def players_in_pot(self) -> Iterator[int]:
        """
        Returns:
            Iterator[int]: An iterator over the player player_id's that have a stake in this pot.

        """

        return iter(self.player_amounts.keys())

    def collect_bets(self):
        """
        Collects all the bets players made this round and adds them to
        the total amount. Resets player betting.
        """
        self.raised = 0
        for player_id, player_amount in self.player_amounts.items():
            self.amount += player_amount
            self.player_amounts[player_id] = 0

    def remove_player(self, player_id: int):
        """
        Removes the given player from the pot and adds their betting
        to the total amount.

        Arguments:
            player_id (int): Player player_id

        """
        if player_id not in self.player_amounts:
            return

        self.amount += self.player_amounts.pop(player_id)

    def get_amount(self) -> int:
        """
        Returns:
            int: How many chips this pot contains not including the current round of betting.

        """

        return self.amount

    def get_total_amount(self) -> int:
        """
        Returns:
            int: How many chips this pot contains including the current round of betting.

        """

        return sum(self.player_amounts.values()) + self.get_amount()

    def split_pot(self, raised_level: int) -> Optional[Pot]:
        """
        Returns a pot with players and the overflow over the raised_level

        Arguments:
            raised_level (int): The chip count to cut off at
        Returns:
            Optional[Pot]: The new pot or None if self.raised <= raised_level
        """
        if self.raised <= raised_level:
            return None

        split_pot = Pot()
        self.raised = raised_level

        for player_id in self.players_in_pot():
            # player currently in last pot, post overflow to the split pot
            if self.get_player_amount(player_id) > self.raised:
                overflow = self.get_player_amount(player_id) - self.raised
                split_pot.player_post(player_id, overflow)
                self.player_amounts[player_id] -= overflow

        return split_pot


class GameState(Enum):
    """An enum representing the state of the game (not just one hand)"""

    RUNNING = auto()
    """The table is active and is able to play hands."""

    STOPPED = auto()
    """The table is inactive due to lack of players or lack
    of chips and unable to play hands."""


class TexasHoldEm:
    # pylint: disable=too-many-instance-attributes,stop-iteration-return

    """
    Represents a table of TexasHoldEm (tournament style).

    Instantiate this object with the buyin, big blind, small blind,
    and the number of players.

    To interact with this class, call :meth:`TexasHoldEm.start_hand` which will
    run the PREHAND phase (move/post blinds, reset pots, deal cards, etc.)

    To input an action at each stage, call :meth:`TexasHoldEm.take_action` which will
    execute the given action for the current player.

    """

    def __init__(self, buyin: int, big_blind: int, small_blind: int, max_players=9):
        """
        Arguments:
            buyin (int): The buyin to register for this game.
            big_blind (int): Big blind
            small_blind (int): Small blind
            max_players (int): how many players can sit at the table, defaults to 9.
        """
        self.buyin = buyin
        self.big_blind = big_blind
        self.small_blind = small_blind
        self.max_players = max_players

        self.players: list[Player] = list(Player(i, self.buyin) for i in range(max_players))

        self.btn_loc = random.choice(self.players).player_id
        self.bb_loc = -1
        self.sb_loc = -1
        self.current_player = -1

        self.pots = []
        self.starting_pot = 0
        self._deck = None
        self.board = []
        self.hands = {}

        self.num_hands = 0
        self.hand_phase = HandPhase.PREHAND
        self.game_state = GameState.RUNNING

        self._handstate_handler: Dict[HandPhase, Callable[[], Optional[Iterator[TexasHoldEm]]]] = {
            HandPhase.PREHAND: self._prehand,
            HandPhase.PREFLOP: lambda: self._betting_round(HandPhase.PREFLOP),
            HandPhase.FLOP: lambda: self._betting_round(HandPhase.FLOP),
            HandPhase.TURN: lambda: self._betting_round(HandPhase.TURN),
            HandPhase.RIVER: lambda: self._betting_round(HandPhase.RIVER),
            HandPhase.SETTLE: self._settle
        }

        self.hand_history: Optional[History] = None
        self._action = None, None
        self._hand_gen = None

    def _prehand(self):
        """
        Handles skips, not enough chips, rotation and posting of blinds,
        dealing cards and setup for preflop.
        """
        if self.hand_phase != HandPhase.PREHAND:
            raise ValueError("Not time for prehand!")

        # set statuses for players
        for player_id in self.player_iter(loc=0):
            self.players[player_id].last_pot = 0

            if self.players[player_id].chips == 0:
                self.players[player_id].state = PlayerState.SKIP
            else:
                self.players[player_id].state = PlayerState.TO_CALL

        active_players = list(self.active_iter(self.btn_loc + 1))

        # stop if only 1 player
        if len(active_players) <= 1:
            self.game_state = GameState.STOPPED
            return

        # change btn loc (at least 2 players)
        self.btn_loc = active_players[0]
        self.sb_loc = active_players[1]

        # heads up edge case => sb = btn
        if len(active_players) == 2:
            self.sb_loc = self.btn_loc

        self.bb_loc = next(self.active_iter(self.sb_loc + 1))

        # reset pots
        self.pots = [Pot()]
        self.pots[0].amount = self.starting_pot

        # deal cards
        self._deck = Deck()
        self.hands = {}
        self.board = []

        for player_id in self.active_iter(self.btn_loc + 1):
            self.hands[player_id] = self._deck.draw(num=2)

        # reset history
        self._action = None, None
        self.hand_history = History(
            prehand=PrehandHistory(
                btn_loc=self.btn_loc,
                big_blind=self.big_blind,
                small_blind=self.small_blind,
                starting_pot=self.starting_pot,
                player_chips={
                    i: self.players[i].chips
                    for i in range(self.max_players)
                },
                player_cards=self.hands
            )
        )

        # reset left over
        self.starting_pot = 0

        # post blinds
        self._player_post(self.sb_loc, self.small_blind)
        self._player_post(self.bb_loc, self.big_blind)

        # action to left of BB
        self.current_player = next(self.active_iter(loc=self.bb_loc + 1))
        self.num_hands += 1

    def player_iter(self, loc: int = None, reverse: bool = False) -> Iterator[int]:
        """
        Iterates through all players starting at player_id and rotating in order
        of increasing player_id.

        Arguments:
            loc (int): The player_id to start at, default is current_player.
            reverse (bool): In reverse play order, default False
        Returns:
            (Iterator[int]): An iterator over all the players.
        """
        if loc is None:
            loc = self.current_player

        start, stop, step = loc, loc + self.max_players, 1
        if reverse:
            start, stop, step = stop, start, -step

        for i in range(start, stop, step):
            yield i % self.max_players

    def active_iter(self, loc: int = None, reverse: bool = False) -> Iterator[int]:
        """
        Iterates through all "active" players (i.e. all players without statuses
        OUT or SKIP).

        Arguments:
            loc (int): The location to start at, defaults to current_player
            reverse (bool): In reverse play order, default False
        Returns:
            Iterator[int]: An iterator over all active players starting at loc
        """
        if loc is None:
            loc = self.current_player
        for player_id in self.player_iter(loc=loc, reverse=reverse):
            if self.players[player_id].state not in (PlayerState.OUT, PlayerState.SKIP):
                yield player_id

    def in_pot_iter(self, loc: int = None, reverse: bool = False) -> Iterator[int]:
        """
        Iterates through all active players, that can take an action.
        Iterates thru self.active_iter() and finds players with state
        IN or TO_CALL (i.e. not including ALL_IN).

        Arguments:
            loc (int): The location to start at, defaults to current_player
            reverse (bool): In reverse play order, default False
        Returns:
            Iterator[int]: An iterator over active players who can take an action.
        """
        if loc is None:
            loc = self.current_player
        for player_id in self.active_iter(loc=loc, reverse=reverse):
            if self.players[player_id].state in (PlayerState.IN, PlayerState.TO_CALL):
                yield player_id

    def _split_pot(self, pot_id: int, raised_level: int):
        """
        Splits the given pot at the given raised level, and adds players with
        excess to the new pot.

        Arguments:
            pot_id (int)            - The pot to split
            raised_level (int)      - The chip count to cut off at

        """
        pot = self._get_pot(pot_id)
        split_pot = pot.split_pot(raised_level)

        if not split_pot:
            return

        self.pots.insert(pot_id + 1, split_pot)

        for player_id in self.in_pot_iter():
            if self.players[player_id].chips >= self.chips_to_call(player_id):
                self.players[player_id].last_pot += 1

    def _player_post(self, player_id: int, amount: int):
        """
        Let a player post the given amount and sets the corresponding board state
        (i.e. makes other player states TO_CALL, sets ALL_IN). Also handles all
        pots (i.e. split pots).

        Arguments:
            player_id (int) - The player_id of the player posting
            amount (int)	- The amount to post
        """
        amount = min(self.players[player_id].chips, amount)
        original_amount = amount
        last_pot = self.players[player_id].last_pot
        chips_to_call = self._get_pot(last_pot).chips_to_call(player_id)

        # if a player posts, they are in the pot
        if amount == self.players[player_id].chips:
            self.players[player_id].state = PlayerState.ALL_IN
        else:
            self.players[player_id].state = PlayerState.IN

        # call in previous pots
        for i in range(last_pot):
            amount = amount - self._get_pot(i).chips_to_call(player_id)
            self.pots[i].player_post(player_id, self.pots[i].chips_to_call(player_id))

        self._get_pot(last_pot).player_post(player_id, amount)

        # players previously in pot need to call in event of a raise
        if amount > chips_to_call:
            for pot_player_id in self._get_pot(last_pot).players_in_pot():
                if self._get_pot(last_pot).chips_to_call(pot_player_id) > 0 and \
                   self.players[pot_player_id].state == PlayerState.IN:
                    self.players[pot_player_id].state = PlayerState.TO_CALL

        # if a player is all_in in this pot, split a new one off
        if PlayerState.ALL_IN in (self.players[i].state
                                  for i in self._get_pot(last_pot).players_in_pot()):
            raised_level = min(self._get_pot(last_pot).get_player_amount(i)
                               for i in self._get_pot(last_pot).players_in_pot()
                               if self.players[i].state == PlayerState.ALL_IN)
            self._split_pot(last_pot, raised_level)

        self.players[player_id].chips = self.players[player_id].chips - original_amount

    def _get_pot(self, pot_id: int) -> Pot:
        """
        Arguments:
            pot_id (int): The player_id of the pot to get
        Returns:
            Pot: The pot with given player_id
        Raises:
            ValueError: If a pot with player_id pot_id does not exist.

        """
        if pot_id >= len(self.pots):
            raise ValueError(f"Pot with player_id {pot_id} does not exist.")

        return self.pots[pot_id]

    def _get_last_pot(self) -> Pot:
        """
        Returns:
            Pot: The current "active" pot

        """
        return self._get_pot(self._last_pot_id())

    def _last_pot_id(self) -> int:
        """
        Returns:
            int: The pot player_id of the last pot.

        """
        return len(self.pots) - 1

    def _is_hand_over(self) -> bool:
        """
        Returns:
            bool: True if no more actions can be taken by the remaining players.
        """
        count = 0
        for i in self.in_pot_iter():
            if self.players[i].state == PlayerState.TO_CALL:
                return False

            if self.players[i].state == PlayerState.IN:
                count += 1

            if count > 1:
                return False
        return True

    def _settle(self):
        """
        Settles the current hand. If players are all-in, makes sure
        the board has 5 cards before settling.
        """
        if self.hand_phase != HandPhase.SETTLE:
            raise ValueError("Not time for Settle!")

        settle_history = SettleHistory(
            new_cards=[],
            pot_winners={}
        )
        self.hand_history[HandPhase.SETTLE] = settle_history

        self.current_player = next(self.active_iter(loc=self.btn_loc + 1))

        for i, pot in enumerate(self.pots, 0):
            players_in_pot = list(pot.players_in_pot())
            # only player left in pot wins
            if len(players_in_pot) == 1:
                self.players[players_in_pot[0]].chips += pot.get_total_amount()
                settle_history.pot_winners[i] = (pot.get_total_amount(), -1, players_in_pot)
                continue

            # make sure there is 5 cards on the board
            if len(self.board) < 5:
                new_cards = self._deck.draw(num=5 - len(self.board))
                settle_history.new_cards.extend(new_cards)
                self.board.extend(new_cards)

            player_ranks = {}
            for player_id in players_in_pot:
                player_ranks[player_id] = evaluator.evaluate(self.hands[player_id], self.board)

            best_rank = min(player_ranks.values())
            winners = [player_id
                       for player_id, player_rank in player_ranks.items()
                       if player_rank == best_rank]

            settle_history.pot_winners[i] = (pot.get_total_amount(), best_rank, winners)

            win_amount = int((pot.get_total_amount()) / len(winners))
            self.starting_pot = pot.get_total_amount() - (win_amount * len(winners))
            for player_id in winners:
                self.players[player_id].chips += win_amount

    def chips_to_call(self, player_id: int) -> int:
        """
        Arguments:
            player_id (int): The player player_id
        Returns:
            int: The amount of chips the player needs to call in all pots
                to play the hand.
        """
        return sum(self._get_pot(i).chips_to_call(player_id)
                   for i in range(self.players[player_id].last_pot + 1))

    def player_bet_amount(self, player_id: int) -> int:
        """
        Arguments:
            player_id (int): The player player_id
        Returns:
            int: The amount of chips the player bet this round across all
                pots.
        """
        return sum(self._get_pot(i).get_player_amount(player_id) for i in range(len(self.pots)))

    def chips_at_stake(self, player_id: int) -> int:
        """
        Arguments:
            player_id (int) - The player player_id
        Returns:
            int - The amount of chips the player is eligible to win
        """
        return sum(self._get_pot(i).get_total_amount()
                   for i in range(len(self.pots))
                   if player_id in self._get_pot(i).players_in_pot())

    def validate_move(self, player_id: int,
                      action: ActionType,
                      value: Optional[int] = None) -> bool:
        """
        Validate the potentially invalid action for the given player.

        Arguments:
            player_id (int): the player to take action
            action (ActionType): The ActionType to take
            value (int, optional): In the case of raise, how much to raise
        Returns:
            bool: True if the move is valid, False o/w

        """
        # ALL_IN should be translated
        new_action, new_value = action, value
        if new_action == ActionType.ALL_IN:
            new_action, new_value = self._translate_allin(new_action, new_value)

        player_amount = self.player_bet_amount(player_id)
        chips_to_call = self.chips_to_call(player_id)
        raised_level = self._get_pot(self.players[player_id].last_pot).raised

        # Check if player player_id is current player
        if self.current_player != player_id:
            return False

        if new_action == ActionType.CALL:
            return self.players[player_id].state == PlayerState.TO_CALL
        if new_action == ActionType.CHECK:
            return self.players[player_id].state == PlayerState.IN
        if new_action == ActionType.RAISE:
            return not (
               new_value is None or
               (new_value < raised_level + self.big_blind
                and new_value < player_amount + self.players[player_id].chips) or
               player_amount + self.players[player_id].chips < new_value or
               new_value < chips_to_call
            )
        if new_action == ActionType.FOLD:
            return True

        return False

    def _safe_execute(self, player_id: int,
                      action: ActionType,
                      value: Optional[int] = None) -> bool:
        """
        Safely execute the potentially Invalid action for the given player.

        Arguments:
            player_id (int) 				- the player to take action
            action (ActionType) 	- The ActionType to take
            value (Optional[int]) - In the case of raise, how much to raise
        Returns:
            bool - True if successfully executed, False otherwise
        """
        # Validate move
        if not self.validate_move(player_id, action, value):
            return False

        # ALL_IN should be translated
        if action == ActionType.ALL_IN:
            action, value = self._translate_allin(action, value)

        player_amount = self.player_bet_amount(player_id)
        chips_to_call = self.chips_to_call(player_id)

        # Execute move
        if action == ActionType.CALL:
            self._player_post(player_id, chips_to_call)
        elif action == ActionType.CHECK:
            pass
        elif action == ActionType.RAISE:
            self._player_post(player_id, value - player_amount)
        elif action == ActionType.FOLD:
            self.players[player_id].state = PlayerState.OUT
            for i in range(self.players[player_id].last_pot + 1):
                self.pots[i].remove_player(player_id)
        else:
            return False

        return True

    def _translate_allin(self,
                         action: ActionType,
                         value: int = None) -> Tuple[ActionType, Optional[int]]:
        """
        Translates an all-in action to the appropriate action,
        either call or raise.
        """
        if action != ActionType.ALL_IN:
            return action, value

        if self.players[self.current_player].chips <= self.chips_to_call(self.current_player):
            return ActionType.CALL, None

        return ActionType.RAISE, \
            self.player_bet_amount(self.current_player) + self.players[self.current_player].chips

    def _betting_round(self, hand_phase: HandPhase) -> Iterator[TexasHoldEm]:
        """
        Core round of the poker game. Executes actions from each active player
        until everyone "checks"

        Arguments:
            hand_phase (HandPhase) - Which betting round phase to execute
        Raises:
            ValueError             - If self.hand_state is not a valid betting round
        """

        if hand_phase not in (HandPhase.PREFLOP, HandPhase.FLOP, HandPhase.TURN, HandPhase.RIVER):
            raise ValueError("Not valid betting round!")

        if hand_phase != self.hand_phase:
            raise ValueError(f"Hand phase mismatch: expected {self.hand_phase}, got {hand_phase}")

        # add new cards to the board
        new_cards = self._deck.draw(num=hand_phase.new_cards())
        self.hand_history[hand_phase] = BettingRoundHistory(
            new_cards=new_cards,
            actions=[]
        )
        self.board.extend(new_cards)

        # player to the left of the button starts
        if hand_phase != HandPhase.PREFLOP:
            self.current_player = next(self.active_iter(loc=self.btn_loc + 1))

        first_pot = self._last_pot_id()
        player_iter = self.in_pot_iter(self.current_player)

        while not self._is_hand_over():
            try:
                self.current_player = next(player_iter)
            except StopIteration:
                break

            yield self

            action, val = self._translate_allin(*self._action)
            passed = self._safe_execute(self.current_player, action, val)

            if not passed:
                raise ValueError(f"Invalid move for player {self.current_player}: "
                                 f"{action}, {val}")

            betting_history = self.hand_history[self.hand_phase]
            betting_history.actions.append(PlayerAction(
                player_id=self.current_player,
                action_type=action,
                value=val)
            )

            # On raise, everyone eligible gets to take another action
            if action == ActionType.RAISE:
                player_iter = self.in_pot_iter(self.current_player)

                # Throwaway current player
                # Edge case: _in_pot_iter already excludes ALL_IN
                if self.players[self.current_player].state != PlayerState.ALL_IN:
                    next(player_iter)

        # consolidate betting to all pots in this betting round
        for i in range(first_pot, len(self.pots)):
            self._get_pot(i).collect_bets()

    def get_hand(self, player_id) -> list[Card]:
        """
        Arguments:
            player_id (int): The player_id of the player
        Returns:
            list[Card]: A two element list of the hand of the given player,
                if player has not been dealt a hand, returns an empty list

        """
        return self.hands.get(player_id, [])

    def start_hand(self):
        """
        Starts a new hand.

        Raises:
            (ValueError)            - If hand already in progress.
        """
        if self.is_hand_running():
            raise ValueError('In the middle of a hand!')

        self.hand_phase = HandPhase.PREHAND
        self._handstate_handler[self.hand_phase]()

        if self.game_state == GameState.STOPPED:
            return

        self.hand_phase = self.hand_phase.next_phase()
        self._hand_gen = self._hand_iter()

        try:
            next(self._hand_gen)
        except StopIteration:
            pass

    def take_action(self, action_type: ActionType, value: Optional[int] = None):
        """
        The current player takes the specified action.

        Arguments:
            action_type (ActionType) - The action type
            value (Optional[int])    - The value
        Raises:
            (ValueError)            - If no action can be taken due to GameState.STOPPED
                                      or if the move is invalid.

        """
        if not self.is_hand_running():
            raise ValueError("No hand is running")

        if not self.validate_move(self.current_player, action_type, value=value):
            raise ValueError("Move is invalid!")

        self._action = (action_type, value)

        try:
            next(self._hand_gen)
        except StopIteration:
            pass

    def _hand_iter(self) -> Iterator[TexasHoldEm]:
        """
        Returns:
            (Iterator[TexasHoldEm])	- A generator over every intermediate game state.
                                      i.e. right before every action.
        Raises:
            (ValueError)            - If phase != PREFLOP
        """
        if self.hand_phase != HandPhase.PREFLOP:
            raise ValueError("Cannot iterate over hand: not time for PREFLOP")

        while self.is_hand_running():
            if self._is_hand_over():
                self.hand_phase = HandPhase.SETTLE

            round_iter: Optional[Iterator[TexasHoldEm]] = self._handstate_handler[self.hand_phase]()
            if round_iter:
                yield from round_iter

            self.hand_phase = self.hand_phase.next_phase()

    def is_hand_running(self) -> bool:
        """
        Returns:
            bool: True if there is a hand running, false o/w

        """
        return self.hand_phase != HandPhase.PREHAND

    def is_game_running(self) -> bool:
        """
        Returns:
            bool: True if the game is running, false o/w

        """
        return self.game_state == GameState.RUNNING

    def export_history(self, path: Union[str, os.PathLike] = "./texas.pgn") -> os.PathLike:
        """
        Exports the hand history to a human-readable file. If a directory is given,
        finds a name of the form texas(n).pgn to export to.

        Arguments:
            path (Union[str, os.PathLike]): The directory or file to export the history to,
                defaults to the current working directory (./texas.pgn)
        Returns:
            os.PathLike: The path to the history file
        """
        return self.hand_history.export_history(path)

    @staticmethod
    def import_history(path: Union[str, os.PathLike]) -> Iterator[TexasHoldEm]:
        """
        Arguments:
            path (Union[str, os.PathLike]): The PGN file to import from
        Returns:
            Iterator[TexasHoldEm]: An iterator over game states such that
                the next hand will play exactly like from the history.
        Raises:
            HistoryImportError: If the file given does not exist or if the file is invalid
        """
        return TexasHoldEm._import_history(History.import_history(path))

    @staticmethod
    def _import_history(history: History) -> Iterator[TexasHoldEm]:
        """
        Arguments:
            history (History): The History file to import from
        Returns:
            Iterator[TexasHoldEm]: An iterator over game states such that
                the next hand will play exactly like from the history.
        Raises:
            HistoryImportError: If there was an error running the history.
        """
        # pylint: disable=protected-access
        num_players = len(history.prehand.player_chips)
        game = TexasHoldEm(buyin=1,
                           big_blind=history.prehand.big_blind,
                           small_blind=history.prehand.small_blind,
                           max_players=num_players)

        # button placed right before 0
        game.btn_loc = num_players - 1

        # read chips
        for i in game.player_iter(0):
            game.players[i].chips = history.prehand.player_chips[i]
        game.starting_pot = history.prehand.starting_pot

        # stack deck
        deck = Deck()
        deck.cards = list(history.settle.new_cards)

        # player actions in a stack
        player_actions: List[Tuple[int, ActionType, Optional[int]]] = []
        for bet_round in (history.river,
                          history.turn,
                          history.flop,
                          history.preflop):
            if bet_round:
                deck.cards = bet_round.new_cards + deck.cards
                for action in reversed(bet_round.actions):
                    player_actions.insert(0, (action.player_id, action.action_type, action.value))

        # start hand (deck will deal)
        game.start_hand()

        # give players old cards
        for i in game.player_iter():
            game.hands[i] = history.prehand.player_cards[i]

        # swap decks
        game._deck = deck

        while game.is_hand_running():
            yield game

            try:
                player_id, action, value = player_actions.pop(0)
            except IndexError as err:
                raise HistoryImportError("Expected more actions than "
                                         "given in the history file.") from err

            if player_id != game.current_player:
                raise HistoryImportError(f"Error replaying history: action player {player_id} "
                                         f"is not current player {game.current_player}")

            game.take_action(action, value)
        yield game
