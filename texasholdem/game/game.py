# pylint: disable=too-many-lines
"""
The game module includes lightweight data classes:

    - :class:`Player`
    - :class:`Pot`
    - :class:`GameState`

It also includes the main :class:`TexasHoldEm` class.

"""
from __future__ import annotations
import os
from typing import Iterator, Callable, Dict, Tuple, Optional, Union, List, Iterable
from enum import Enum, auto
import random
import warnings

from texasholdem.card.card import Card
from texasholdem.card.deck import Deck
from texasholdem.game.history import (History, PrehandHistory,
                                      BettingRoundHistory, PlayerAction,
                                      HistoryImportError, SettleHistory)
from texasholdem.game.action_type import ActionType
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.player_state import PlayerState
from texasholdem.evaluator import evaluator
from texasholdem.util.functions import check_raise


class Player:
    # pylint: disable=too-few-public-methods
    """
    The :class:`TexasHoldEm` class uses this
    class as a bookkeeping mechanism.

    Attributes:
        player_id (int): The player id
        chips (int): The number of chips the player has behind them
        state (PlayerState): The player state
        last_pot (int): The pot id of the last pot the player is eligible for.

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

    Attributes:
        amount (int): The amount of chips in the pot NOT including the current betting round
        raised (int): The highest bet amount in the current betting round
        player_amounts (dict[int, int]): A map from player id to # chips each player has posted
                                         this round

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
            int: The amount the player needs to call to be in this pot.
              This is just :attr:`raised` if the player hasn't bet yet.

        """
        return self.raised - self.player_amounts.get(player_id, 0)

    def player_post(self, player_id: int, amount: int):
        """
        The given player posts amount into this pot. If the total amount for the player
        exceeds the current :attr:`raised` value, sets it anew.

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
            player_id (int): The player id
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
            player_id (int): The player id

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
            Pot, optional: The new Pot or None if self.raised <= raised_level

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

    Arguments:
        buyin (int): The buyin to register for this game.
        big_blind (int): Big blind
        small_blind (int): Small blind
        max_players (int): how many players can sit at the table, defaults to 9.
    Attributes:
        buyin (int): The buyin to register for this game.
        big_blind (int): Big blind
        small_blind (int): Small blind
        max_players (int): how many players can sit at the table, defaults to 9.
        players (list[Player]): A list of all players in the game.
        btn_loc (int): The id of the player who has the button.
        bb_loc (int): The id of the player who has the big blind.
        sb_loc (int): The id of the player who has the small blind.
        current_player (int): The id of the player who is to act.
        pots (list[Pot]): The active :class:`Pot` objects in the game.
        board (list[Card]): The communal cards that are out.
        hands (dict[int, list[Card]]): Map from player id to their hand
        last_raise (int): The amount of the last raise (that was over the previous bet)
        raise_option (bool): If the current player has the option to raise (not taking into account
            chip count). This is usually true and is only useful in the context of WSOP 2021 Rule 96
            regarding when an all-in raise action does not trigger another round of betting.
        num_hands (int): The number of hands played so far.
        hand_phase (HandPhase): The current hand phase
        game_state (GameState): The current GameState
        hand_history (History): The history of the current hand.

    """

    def __init__(self, buyin: int, big_blind: int, small_blind: int, max_players=9):
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
        self._deck = None
        self.board = []
        self.hands = {}
        self.last_raise = 0
        self.raise_option = True

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

        active_players = list(self.in_pot_iter(self.btn_loc + 1))

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

        self.bb_loc = next(self.in_pot_iter(self.sb_loc + 1))

        # reset pots
        self.pots = [Pot()]

        # deal cards
        self._deck = Deck()
        self.hands = {}
        self.board = []

        for player_id in self.in_pot_iter(self.btn_loc + 1):
            self.hands[player_id] = self._deck.draw(num=2)

        # reset history
        self._action = None, None
        self.raise_option = True
        self.hand_history = History(
            prehand=PrehandHistory(
                btn_loc=self.btn_loc,
                big_blind=self.big_blind,
                small_blind=self.small_blind,
                player_chips={
                    i: self.players[i].chips
                    for i in range(self.max_players)
                },
                player_cards=self.hands
            )
        )

        # post blinds
        self._player_post(self.sb_loc, self.small_blind)
        self._player_post(self.bb_loc, self.big_blind)
        self.last_raise = 0

        # action to left of BB
        self.current_player = next(self.in_pot_iter(loc=self.bb_loc + 1))
        self.num_hands += 1

    def player_iter(self,
                    loc: int = None,
                    reverse: bool = False,
                    match_states: Iterable[PlayerState] = tuple(PlayerState),
                    filter_states: Iterable[PlayerState] = ()) -> Iterator[int]:
        """
        Iterates through all players starting at player_id and rotating in order
        of increasing player id.

        Arguments:
            loc (int, optional): The player_id to start at, default is :attr:`current_player`.
            reverse (bool): In reverse play order, default False
            match_states (Iterable[PlayerState]): Only include players with the given states
            filter_states (Iterable[PlayerState]): Exclude players with the given states
        Returns:
            Iterator[int]: An iterator over all player ids.

        """
        if loc is None:
            loc = self.current_player

        start, stop, step = loc, loc + self.max_players, 1
        if reverse:
            start, stop, step = stop, start, -step

        for i in range(start, stop, step):
            if self.players[i % self.max_players].state not in filter_states \
                    and self.players[i % self.max_players].state in match_states:
                yield i % self.max_players

    def in_pot_iter(self, loc: int = None, reverse: bool = False) -> Iterator[int]:
        """
        Iterates through all players with a stake in the pot (i.e. all players without
        states :obj:`~texasholdem.game.player_state.PlayerState.OUT` or
        :obj:`~texasholdem.game.player_state.PlayerState.SKIP`

        Arguments:
            loc (int, optional): The location to start at, defaults to current_player
            reverse (bool): In reverse play order, default False
        Returns:
            Iterator[int]: An iterator over all active player ids starting at loc

        """
        if loc is None:
            loc = self.current_player
        yield from self.player_iter(loc=loc,
                                    reverse=reverse,
                                    filter_states=(PlayerState.OUT,
                                                   PlayerState.SKIP))

    def active_iter(self, loc: int = None, reverse: bool = False) -> Iterator[int]:
        """
        Iterates through all players that can take an action.
        i.e. players with states :obj:`~texasholdem.game.player_state.PlayerState.IN`
        or :obj:`~texasholdem.game.player_state.PlayerState.TO_CALL` (not including
        :obj:`~texasholdem.game.player_state.PlayerState.ALL_IN`).

        Arguments:
            loc (int, optional): The location to start at, defaults to current_player
            reverse (bool): In reverse play order, default False
        Returns:
            Iterator[int]: An iterator over active players who can take an action.

        """
        if loc is None:
            loc = self.current_player
        yield from self.player_iter(loc=loc,
                                    reverse=reverse,
                                    match_states=(PlayerState.TO_CALL,
                                                  PlayerState.IN))

    def _split_pot(self, pot_id: int, raised_level: int):
        """
        Splits the given pot at the given raised level, and adds players with
        excess to the new pot.

        Arguments:
            pot_id (int): The pot to split
            raised_level (int): The chip count to cut off at

        """
        pot = self._get_pot(pot_id)
        split_pot = pot.split_pot(raised_level)

        if not split_pot:
            return

        self.pots.insert(pot_id + 1, split_pot)

        for player_id in self.active_iter():
            if self.players[player_id].chips > self.chips_to_call(player_id):
                self.players[player_id].last_pot += 1

    def _player_post(self, player_id: int, amount: int):
        """
        Let a player post the given amount and sets the corresponding board state
        (i.e. makes other player states TO_CALL, sets ALL_IN). Also handles all
        pots (i.e. split pots).

        Arguments:
            player_id (int): The player_id of the player posting
            amount (int): The amount to post

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
            self.last_raise = max(amount - self.last_raise, self.last_raise)
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
            pot_id (int): The id of the pot to get
        Returns:
            Pot: The pot with given id
        Raises:
            ValueError: If a pot with id pot_id does not exist.

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
        for i in self.active_iter():
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

        self.current_player = next(self.in_pot_iter(loc=self.btn_loc + 1))

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
            for player_id in winners:
                self.players[player_id].chips += win_amount

            # leftover chip goes to player left of the button WSOP Rule 73
            leftover = pot.get_total_amount() - (win_amount * len(winners))
            if leftover:
                for j in self.in_pot_iter(loc=self.btn_loc):
                    if j in winners:
                        self.players[j].chips += leftover
                        break

    def chips_to_call(self, player_id: int) -> int:
        """
        Arguments:
            player_id (int): The player id
        Returns:
            int: The amount of chips the player needs to call in all pots to play the hand.

        """
        return sum(self._get_pot(i).chips_to_call(player_id)
                   for i in range(self.players[player_id].last_pot + 1))

    def player_bet_amount(self, player_id: int) -> int:
        """
        Arguments:
            player_id (int): The player player_id
        Returns:
            int: The amount of chips the player bet this round across all pots.

        """
        return sum(self._get_pot(i).get_player_amount(player_id) for i in range(len(self.pots)))

    def chips_at_stake(self, player_id: int) -> int:
        """
        Arguments:
            player_id (int) - The player player_id
        Returns:
            int: The amount of chips the player is eligible to win

        """
        return sum(self._get_pot(i).get_total_amount()
                   for i in range(len(self.pots))
                   if player_id in self._get_pot(i).players_in_pot())

    def total_to_value(self, total: Optional[int], player_id: int) -> Optional[int]:
        """
        Translates a raise phrase "raise *to* total" to the phrase
        "raise value".

        Arguments:
            total (int, optional): A total amount to raise
            player_id (int): The player who's doing the raising
        Returns:
            Optional[int]: A translation to an amount the player is raising *to*
        """
        if not total:
            return None
        return total - self.chips_to_call(player_id) - self.player_bet_amount(player_id)

    def value_to_total(self, value: Optional[int], player_id: int) -> Optional[int]:
        """
        Translates a raise phrase "raise value" to the phrase
        "raise *to* total".

        Arguments:
            value (int, optional): An amount to raise past the any other bet
            player_id (int): The player who's doing the raising
        Returns:
            Optional[int]: A translation to an amount the player is raising *by*
        """
        if not value:
            return None
        return value + self.chips_to_call(player_id) + self.player_bet_amount(player_id)

    def min_raise(self):
        """
        Returns:
            The minimum amount a player can raise by.
        """
        return max(self.big_blind, self.last_raise)

    @check_raise(ValueError)
    def validate_move(self,
                      player_id: Optional[int] = None,
                      action: Optional[ActionType] = None,
                      value: Optional[int] = None,
                      total: Optional[int] = None,
                      throws: bool = False):
        # pylint: disable=unused-argument,too-many-arguments,
        # pylint: disable=too-many-branches,too-many-return-statements
        """
        Validate the potentially invalid action for the given player.

        .. note::
            :code:`value` and :code:`total` are mutually exclusive.

        .. deprecated:: 0.6
            The :code:`value` argument will be redefined in 1.0. Currently, :code:`value`
            and :code:`total` mean to raise *to* the amount given. In 1.0, :code:`value`
            will mean to raise an amount more than the current bet amount.

        Arguments:
            player_id (int, optional): The player to take action. Default current_player.
            action (int, optional): The ActionType to take
            value (int, optional): For a raise action, how much to raise *to*.
            total (int, optional): For a raise action, how much to raise *to*.
            throws (bool): If true, will throw an Exception instead if
                the move is invalid. Default False.
        Returns:
            bool: True if the move is valid, False otherwise.
        Raises:
            ValueError: If move is invalid and throws is True

        """
        if player_id is None:
            player_id = self.current_player

        if total and value:
            raise ValueError("Got arguments for both total and value. Expected only one.")

        if value:
            warnings.warn("The value argument will be redefined in 1.0. Currently, value "
                          "and total mean to raise *to* the amount given. In 1.0, value will "
                          "mean to raise an amount more than the current bet amount.",
                          DeprecationWarning)
            total = value

        # ALL_IN should be translated
        new_action, new_total = action, total
        if new_action == ActionType.ALL_IN:
            new_action, new_total = self._translate_allin(new_action, new_total)

        player_amount = self.player_bet_amount(player_id)
        chips_to_call = self.chips_to_call(player_id)

        if not action:
            return False, "Action is None."

        if self.current_player != player_id:
            return False, f"Player {player_id} is not the current " \
                          f"player (Current player {self.current_player})"

        if new_action == ActionType.CALL and \
                self.players[player_id].state != PlayerState.TO_CALL:
            return False, f"Player {player_id} has state " \
                          f"{self.players[player_id].state} cannot CALL"

        if new_action == ActionType.CHECK and \
                self.players[player_id].state != PlayerState.IN:
            return False, \
                   f"Player {player_id} has state {self.players[player_id]} cannot CHECK"

        if new_action == ActionType.RAISE:
            if new_total is None:
                return False, "Expected value to not be None for action RAISE."

            if not self.raise_option:
                return False, "Betting round is over at this point, can only CALL or FOLD."

            if (self.total_to_value(new_total, player_id) < self.min_raise()
               and new_total < player_amount + self.players[player_id].chips):
                return False, f"Cannot raise {self.total_to_value(new_total, player_id)}, " \
                              f"less than the min raise {self.min_raise()} and player " \
                              f"{player_id} is not going all-in."
            if player_amount + self.players[player_id].chips < new_total:
                return False, f"Cannot raise {new_total}, more than the number of chips " \
                              f"available {player_amount + self.players[player_id].chips}"
            if new_total < chips_to_call:
                return False, f"Expected raise value {new_total} to be more " \
                              f"than the chips to call {chips_to_call}"
        return True, ""

    def _take_action(self,
                     action: ActionType,
                     total: Optional[int] = None):
        """
        Execute the action for the current player. Assumes the move is valid.

        Arguments:
            action (ActionType): The ActionType to take
            total (int, optional): In the case of raise, how much to raise *to*

        """
        # ALL_IN should be translated
        if action == ActionType.ALL_IN:
            action, total = self._translate_allin(action, total=total)

        player_amount = self.player_bet_amount(self.current_player)
        chips_to_call = self.chips_to_call(self.current_player)

        # Execute move
        if action == ActionType.CALL:
            self._player_post(self.current_player, chips_to_call)
        elif action == ActionType.CHECK:
            pass
        elif action == ActionType.RAISE:
            self._player_post(self.current_player, total - player_amount)
        elif action == ActionType.FOLD:
            self.players[self.current_player].state = PlayerState.OUT
            for i in range(self.players[self.current_player].last_pot + 1):
                self.pots[i].remove_player(self.current_player)

    def _translate_allin(self,
                         action: ActionType,
                         total: int = None) -> Tuple[ActionType, Optional[int]]:
        """
        Translates an all-in action to the appropriate action,
        either call or raise.

        """
        if action != ActionType.ALL_IN:
            return action, total

        if self.players[self.current_player].chips <= self.chips_to_call(self.current_player):
            return ActionType.CALL, None

        return ActionType.RAISE, \
            self.player_bet_amount(self.current_player) + self.players[self.current_player].chips

    def _previous_all_in_sum(self, history_len: int) -> int:
        """
        Used for WSOP Rule 96

        Arguments:
            history_len (int): How far back to go
        Returns:
            int: The sum of the raise values of the most recent all-in raise players.
        """
        raised_sum = 0

        for action in reversed(self.hand_history[self.hand_phase].actions[-history_len:]):
            if self.players[action.player_id].state == PlayerState.ALL_IN \
                    and action.action_type == ActionType.RAISE:
                raised_sum += action.value
            elif self.players[action.player_id].state == PlayerState.IN:
                break

        return raised_sum

    def _betting_round(self, hand_phase: HandPhase) -> Iterator[TexasHoldEm]:
        """
        Core round of the poker game. Executes actions from each active player
        until everyone "checks"

        Arguments:
            hand_phase (HandPhase): Which betting round phase to execute
        Raises:
            ValueError: If self.hand_state is not a valid betting round

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

        # reset last raise
        first_pot = self._last_pot_id()
        self.last_raise = 0
        self.raise_option = True

        # player to the left of the button starts
        self.current_player = self.btn_loc + 1
        if hand_phase == HandPhase.PREFLOP:
            self.current_player = self.bb_loc + 1

        i, player_list = 0, list(self.active_iter(self.current_player))

        while not self._is_hand_over():
            # WSOP 2021 Rule 96
            # if no more active players that can raise continue with the players to call
            # while disabling the raise availability.
            if i >= len(player_list):
                i, player_list = 0, list(self.player_iter(loc=self.current_player + 1,
                                                          match_states=(PlayerState.TO_CALL,)))
                if not player_list:
                    break

                self.raise_option = False

            # book keeping
            prev_raised = self.last_raise

            # set the current player and yield
            self.current_player = player_list[i]
            yield self

            action, total = self._translate_allin(*self._action)
            value = self.total_to_value(total=total,
                                        player_id=self.current_player)
            self.validate_move(action=action, total=total, throws=True)

            betting_history = self.hand_history[self.hand_phase]
            betting_history.actions.append(PlayerAction(
                player_id=self.current_player,
                action_type=action,
                total=total,
                value=value)
            )

            self._take_action(action, total=total)

            # On raise, everyone eligible gets to take another action
            if action == ActionType.RAISE:
                # WSOP 2021 Rule 96
                # An all-in raise less than the previous raise shall not reopen
                # the bidding unless two or more such all-in raises total greater
                # than or equal to the previous raise.
                raise_sum = self._previous_all_in_sum(len(player_list))
                if value < prev_raised:
                    if raise_sum < prev_raised:
                        i += 1
                        continue
                    # Exception for rule 96, set this
                    self.last_raise = raise_sum

                # reset the round (i.e. as if the betting round started here)
                i, player_list = 0, list(self.active_iter(self.current_player))

                # Throwaway current player
                # Edge case: active_iter already excludes ALL_IN
                if self.players[self.current_player].state != PlayerState.ALL_IN:
                    player_list.pop(0)
            else:
                i += 1

        # consolidate betting to all pots in this betting round
        for i in range(first_pot, len(self.pots)):
            self._get_pot(i).collect_bets()

    def get_hand(self, player_id) -> list[Card]:
        """
        Arguments:
            player_id (int): The player id
        Returns:
            list[Card]: A two element list of the hand of the given player,
                if the player has not been dealt a hand, returns an empty list

        """
        return self.hands.get(player_id, [])

    def start_hand(self):
        """
        Starts a new hand. Handles :obj:`~texasholdem.game.player_state.PlayerState.SKIP`,
        not enough chips, resetting pots, rotation and posting of blinds, dealing cards, etc.

        Raises:
            ValueError: If a hand already in progress.

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

    def take_action(self,
                    action_type: ActionType,
                    value: Optional[int] = None,
                    total: Optional[int] = None):
        """
        The current player takes the specified action.

        .. note::
            :code:`value` and :code:`total` are mutually exclusive.

        .. deprecated:: 0.6
            The :code:`value` argument will be redefined in 1.0. Currently, :code:`value`
            and :code:`total` mean to raise *to* the amount given. In 1.0, :code:`value`
            will mean to raise an amount more than the current bet amount.

        Arguments:
            action_type (ActionType): The action type
            value (int, optional): For a raise action, how much to raise *to*.
            total (int, optional): For a raise action, how much to raise *to*.
        Raises:
            ValueError: If no hand is running or if the move is invalid.

        """
        if not self.is_hand_running():
            raise ValueError("No hand is running")

        if total and value:
            raise ValueError("Got arguments for both total and value. Expected only one.")

        if value:
            warnings.warn("The value argument will be redefined in 1.0. Currently, value "
                          "and total mean to raise *to* the amount given. In 1.0, value will "
                          "mean to raise an amount more than the current bet amount.",
                          DeprecationWarning)
            total = value

        self.validate_move(action=action_type, total=total, throws=True)
        self._action = (action_type, total)

        try:
            next(self._hand_gen)
        except StopIteration:
            pass

    def _hand_iter(self) -> Iterator[TexasHoldEm]:
        """
        Returns:
            Iterator[TexasHoldEm]: A generator over every intermediate game state.
                i.e. right before every action.
        Raises:
            ValueError: If phase != PREFLOP

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
        finds a name of the form :code:`texas(n).pgn` to export to. PGN files can consequently
        be imported with :meth:`import_history()`.

        Arguments:
            path (str | os.PathLike]): The directory or file to export the history to,
                defaults to the current working directory at the file `./texas.pgn`
        Returns:
            os.PathLike: The path to the history file

        """
        return self.hand_history.export_history(path)

    @staticmethod
    def import_history(path: Union[str, os.PathLike]) -> Iterator[TexasHoldEm]:
        """
        Import a PGN file i.e. as exported from :meth:`export_history()`. Returns an
        iterator over game states as specified from the history.

        Arguments:
            path (str | os.PathLike): The PGN file to import from
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
                    player_actions.insert(0, (action.player_id, action.action_type, action.total))

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
                player_id, action, total = player_actions.pop(0)
            except IndexError as err:
                raise HistoryImportError("Expected more actions than "
                                         "given in the history file.") from err

            if player_id != game.current_player:
                raise HistoryImportError(f"Error replaying history: action player {player_id} "
                                         f"is not current player {game.current_player}")

            game.take_action(action, total=total)
        yield game
