from __future__ import annotations

from typing import Iterator, Callable, Dict, Tuple, Union
from enum import Enum, auto
import random

from texasholdem.card.card import Card
from texasholdem.card.deck import Deck
from texasholdem.game.history import *
from texasholdem.game.action_type import ActionType
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.player_state import PlayerState
from texasholdem.evaluator import evaluator
from texasholdem.game.errors import PokerError


class Player:
    """
    The TexasHoldEm object uses this Player as a bookkeeping mechanism for:
        - Chip count
        - PlayerState
        - Which pots the player is in
    """

    def __init__(self, id, chips):
        self.id = id
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

    def chips_to_call(self, id: int) -> int:
        """Returns the amount of chips to call for the given player.

        Args:
            id (int): The id of the player in the pot
        Returns:
            int: The amount the player needs to call to be in this pot
              (this is just self.raised if the player hasn't bet yet)

        """
        return self.raised - self.player_amounts.get(id, 0)

    def player_post(self, id: int, amount: int):
        """The given player posts amount into this pot. If player[id].amount > raised,
        sets new raised value.

        Arguments:
            id (int): The id of the player posting
            amount (int): The amount to post into this pot (can be negative)

        """
        self.player_amounts[id] = self.player_amounts.get(id, 0) + amount

        if self.player_amounts[id] > self.raised:
            self.raised = self.player_amounts[id]

    def get_player_amount(self, id: int) -> int:
        """
        Arguments:
            id (int): Player id
        Returns:
            int: the amount the player has bet currently for this pot.

        """
        return self.player_amounts.get(id, 0)

    def players_in_pot(self) -> Iterator[int]:
        """
        Returns:
            Iterator[int]: An iterator over the player id's that have a stake in this pot.

        """

        return iter(self.player_amounts.keys())

    def collect_bets(self):
        self.raised = 0
        for id in self.player_amounts:
            self.amount += self.player_amounts[id]
            self.player_amounts[id] = 0

    def remove_player(self, id: int):
        if id not in self.player_amounts:
            return

        self.amount += self.player_amounts.pop(id)

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


class GameState(Enum):
    """An enum representing the state of the game (not just one hand)"""

    RUNNING = auto()
    """The table is active and is able to play hands."""

    STOPPED = auto()
    """The table is inactive due to lack of players or lack
    of chips and unable to play hands."""


class TexasHoldEm:
    """
    Represents a table of TexasHoldEm (tournament style).

    Instantiate this object with the buyin, big blind, small blind,
    and the number of players.

    To interact with this class, call :meth:`TexasHoldEm.run_hand` which returns an
    iterator that yields this object over each stage of the game that requires input from
    a player.
    To input an action at each stage, call :meth:`TexasHoldEm.set_action` which will
    use the given action for the next state in the iterator.

    """

    def __init__(self, buyin: int, big_blind: int, small_blind: int, max_players=9):
        """
        Represents a table of TexasHoldEm (tournament style).

        Instantiate this object with the buyin, big blind, small blind,
        and the number of players.

        To interact with this class, call :meth:`TexasHoldEm.run_hand` which returns an
        iterator that yields this object each stage of the game that requires input from
        a player.
        To input an action at each stage, call :meth:`TexasHoldEm.set_action` which will
        use the given action for the next state in the iterator.

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

        self.players: tuple[Player] = tuple(Player(i, self.buyin) for i in range(max_players))

        self.btn_loc = random.randrange(0, max_players)
        self.bb_loc = -1
        self.sb_loc = -1
        self.current_player = -1

        self.pots = []
        self._deck = None
        self.board = []
        self.hands = {}

        self.num_hands = 0
        self.hand_phase = HandPhase.PREHAND
        self.game_state = GameState.RUNNING

        self._handstate_handler: Dict[HandPhase, Callable[[], Iterator[TexasHoldEm]]] = {
            HandPhase.PREHAND: self._prehand,
            HandPhase.PREFLOP: self._preflop,
            HandPhase.FLOP: self._flop,
            HandPhase.TURN: self._turn,
            HandPhase.RIVER: self._river,
            HandPhase.SETTLE: self._settle
        }

        self.hand_history: Dict[HandPhase, Union[PrehandHistory, BettingRoundHistory]] = {}
        self.action = None, None

    def _prehand(self):
        """
        Handles skips, not enough chips, rotation and posting of blinds,
        dealing cards and setup for preflop.
        """
        if self.hand_phase != HandPhase.PREHAND:
            raise PokerError("Not time for prehand!")

        # set statuses for players
        for id in self.player_iter(loc=0):
            self.players[id].last_pot = 0

            if self.players[id].chips == 0:
                self.players[id].state = PlayerState.SKIP
            else:
                self.players[id].state = PlayerState.TO_CALL

        active_players = list(self.active_iter(self.btn_loc + 1))

        # stop if only 1 player
        if len(active_players) <= 1:
            self.game_state = GameState.STOPPED
            yield self

        # change btn loc (at least 2 players)
        self.btn_loc = active_players[0]
        self.sb_loc = active_players[1]

        # heads up edge case => sb = btn
        if len(active_players) == 2:
            self.sb_loc = self.btn_loc

        self.bb_loc = next(self.active_iter(self.sb_loc + 1))

        # reset pots
        self.pots = [Pot()]

        # reset hand history
        self.hand_history = {
            HandPhase.PREHAND: PrehandHistory(
                random_seed=random.getstate(),
                btn_loc=self.btn_loc,
                player_chips={
                    i: self.players[i].chips
                    for i in range(self.max_players)
                }
            )
        }
        self.action = None, None

        # post blinds
        self._player_post(self.sb_loc, self.small_blind)
        self._player_post(self.bb_loc, self.big_blind)

        # deal cards
        self._deck = Deck()
        self.hands = {}
        self.board = []

        for id in self.active_iter(self.btn_loc + 1):
            self.hands[id] = self._deck.draw(n=2)

        # action to left of BB
        self.current_player = next(self.active_iter(loc=self.bb_loc + 1))
        self.num_hands += 1
        yield self

    def player_iter(self, loc: int = None) -> Iterator[int]:
        """
        Iterates through all players starting at id and rotating in order
        of increasing id.

        Arguments:
            loc (int)       - The id to start at, default is current_player.
        Returns:
            (Iterator[int]) - An iterator over all the players.
        """
        if loc is None:
            loc = self.current_player

        for i in range(loc, loc + self.max_players):
            yield i % self.max_players

    def active_iter(self, loc: int = None) -> Iterator[int]:
        """
        Iterates through all "active" players (i.e. all players without statuses
        OUT or SKIP).

        Arguments:
            loc (int)  - The location to start at, defaults to current_player
        Returns:
            (Iterator[int]) - An iterator over all active players starting at loc
        """
        if loc is None:
            loc = self.current_player
        for id in self.player_iter(loc=loc):
            if self.players[id].state not in (PlayerState.OUT, PlayerState.SKIP):
                yield id

    def in_pot_iter(self, loc: int = None) -> Iterator[int]:
        """
        Iterates through all active players, that can take an action.
        Iterates thru self._active_iter() and finds players with state
        IN or TO_CALL (i.e. not including ALL_IN).

        Arguments:
            loc (int)       - The location to start at, defaults to current_player
        Returns:
            (Iterator[int]) - An iterator over active players who can take an action.
        """
        if loc is None:
            loc = self.current_player
        for id in self.active_iter(loc=loc):
            if self.players[id].state in (PlayerState.IN, PlayerState.TO_CALL):
                yield id

    def _split_pot(self, pot_id: int, raised_level: int):
        """
        Splits the given pot at the given raised level, and adds players with
        excess to the new pot.

        Arguments:
            pot_id (int)            - The pot to split
            raised_level (int)      - The chip count to cut off at

        """
        pot = self.get_pot(pot_id)

        if pot.raised <= raised_level:
            return

        split_pot = Pot()

        # Overflow goes to split pot
        split_pot.raised = pot.raised - raised_level
        pot.raised = raised_level

        for id in pot.players_in_pot():
            # player currently in last pot, post overflow to the split pot
            if pot.get_player_amount(id) > pot.raised:
                overflow = pot.get_player_amount(id) - pot.raised
                split_pot.player_post(id, overflow)
                pot.player_post(id, -overflow)

            # increment last_pot for players with enough chips
            if self.players[id].chips >= self.chips_to_call(id):
                self.players[id].last_pot += 1

        self.pots.insert(pot_id + 1, split_pot)

    def _player_post(self, player_id: int, amount: int):
        """
        Let a player post the given amount and sets the corresponding board state
        (i.e. makes other player states TO_CALL, sets ALL_IN). Also handles all
        pots (i.e. split pots).

        Arguments:
            player_id (int) - The ID of the player posting
            amount (int)	- The amount to post
        """
        amount = min(self.players[player_id].chips, amount)
        original_amount = amount
        last_pot = self.players[player_id].last_pot
        chips_to_call = self.get_pot(last_pot).chips_to_call(player_id)

        # if a player posts, they are in the pot
        if amount == self.players[player_id].chips:
            self.players[player_id].state = PlayerState.ALL_IN
        else:
            self.players[player_id].state = PlayerState.IN

        # call in previous pots
        for i in range(last_pot):
            amount = amount - self.get_pot(i).chips_to_call(player_id)
            self.pots[i].player_post(player_id, self.pots[i].chips_to_call(player_id))

        self.get_pot(last_pot).player_post(player_id, amount)

        # players previously in pot need to call in event of a raise
        if amount > chips_to_call:
            for id in self.get_pot(last_pot).players_in_pot():
                if self.get_pot(last_pot).chips_to_call(id) > 0 and \
                   self.players[id].state == PlayerState.IN:
                    self.players[id].state = PlayerState.TO_CALL

        # if a player is all_in in this pot, split a new one off
        if PlayerState.ALL_IN in (self.players[i].state
                                  for i in self.get_pot(last_pot).players_in_pot()):
            raised_level = min(self.get_pot(last_pot).get_player_amount(i)
                               for i in self.get_pot(last_pot).players_in_pot()
                               if self.players[i].state == PlayerState.ALL_IN)
            self._split_pot(last_pot, raised_level)

        self.players[player_id].chips = self.players[player_id].chips - original_amount

    def get_pot(self, pot_id: int) -> Pot:
        """
        Arguments:
            pot_id (int): The ID of the pot to get
        Returns:
            Pot: The pot with given ID
        Raises:
            ValueError: If a pot with ID pot_id does not exist.

        """
        if pot_id >= len(self.pots):
            raise ValueError(f"Pot with id {pot_id} does not exist.")

        return self.pots[pot_id]

    def get_last_pot(self) -> Pot:
        """
        Returns:
            Pot: The current "active" pot

        """
        return self.get_pot(self.get_last_pot_id())

    def get_last_pot_id(self) -> int:
        """
        Returns:
            int: The pot id of the last pot.

        """
        return len(self.pots) - 1

    def _is_hand_over(self) -> bool:
        """
        Returns:
            bool: True if no more actions can be taken by the remaining players.
        """
        count = 0
        for _ in self.in_pot_iter():
            count += 1
            if count > 1:
                return False
        return True

    def _preflop(self) -> Iterator[TexasHoldEm]:
        """
        Runs the PREFLOP sequence
        """
        if self.hand_phase != HandPhase.PREFLOP:
            raise PokerError("Not time for PREFLOP!")

        self.current_player = next(self.active_iter(loc=self.bb_loc + 1))
        yield from self._betting_round()

    def _flop(self) -> Iterator[TexasHoldEm]:
        """
        Runs the FLOP sequence
        """
        if self.hand_phase != HandPhase.FLOP:
            raise PokerError("Not time for PREFLOP!")

        self.board.extend(self._deck.draw(n=3))
        self.current_player = next(self.active_iter(loc=self.btn_loc + 1))
        yield from self._betting_round()

    def _turn(self) -> Iterator[TexasHoldEm]:
        """
        Runs the TURN sequence
        """
        if self.hand_phase != HandPhase.TURN:
            raise PokerError("Not time for Turn!")

        self.board.extend(self._deck.draw(n=1))
        self.current_player = next(self.active_iter(loc=self.btn_loc + 1))
        yield from self._betting_round()

    def _river(self) -> Iterator[TexasHoldEm]:
        """
        Runs the RIVER sequence
        """
        if self.hand_phase != HandPhase.RIVER:
            raise PokerError("Not time for River!")

        self.board.extend(self._deck.draw(n=1))
        self.current_player = next(self.active_iter(loc=self.btn_loc + 1))
        yield from self._betting_round()

    def _settle(self) -> Iterator[TexasHoldEm]:
        """
        Settles the current hand. If players are all-in, makes sure
        the board has 5 card before settling.
        """
        if self.hand_phase != HandPhase.SETTLE:
            raise PokerError("Not time for Settle!")

        self.current_player = next(self.active_iter(loc=self.btn_loc + 1))

        for i in range(len(self.pots)):
            players_in_pot = list(self.pots[i].players_in_pot())
            # only player left in pot wins
            if len(players_in_pot) == 1:
                self.players[players_in_pot[0]].chips += self.pots[i].get_total_amount()
                continue

            # make sure there is 5 cards on the board
            if len(self.board) < 5:
                self.board.extend(self._deck.draw(n=5 - len(self.board)))

            player_ranks = {}
            for id in players_in_pot:
                player_ranks[id] = evaluator.evaluate(self.hands[id], self.board)

            best_rank = min(player_ranks.values())
            winners = [id for id in player_ranks if player_ranks[id] == best_rank]

            win_amount = (self.pots[i].get_total_amount()) / len(winners)
            win_amount = round(win_amount)
            for id in winners:
                self.players[id].chips += win_amount

        yield self

    def chips_to_call(self, id: int) -> int:
        """
        Arguments:
            id (int) - The player id
        Returns:
            int - The amount of chips the player needs to call in all pots
                  to play the hand.
        """
        return sum(self.get_pot(i).chips_to_call(id) for i in range(len(self.pots)))

    def player_bet_amount(self, id: int) -> int:
        """
        Arguments:
            id (int) - The player id
        Returns:
            int - The amount of chips the player bet this round across all
                  pots.
        """
        return sum(self.get_pot(i).get_player_amount(id) for i in range(len(self.pots)))

    def validate_move(self, id: int, action: ActionType, value: Optional[int] = None) -> bool:
        """
        Validate the potentially invalid action for the given player.

        Arguments:
            id (int): the player to take action
            action (ActionType): The ActionType to take
            value (int, optional): In the case of raise, how much to raise
        Returns:
            bool: True if the move is valid, False o/w
        """
        # ALL_IN should be translated
        new_action, new_value = action, value
        if new_action == ActionType.ALL_IN:
            new_action, new_value = self._translate_allin(new_action, new_value)

        player_amount = self.player_bet_amount(id)
        chips_to_call = self.chips_to_call(id)

        # Check if player id is current player
        if self.current_player != id:
            return False

        if new_action == ActionType.CALL:
            return self.players[id].state == PlayerState.TO_CALL
        elif new_action == ActionType.CHECK:
            return self.players[id].state == PlayerState.IN
        elif new_action == ActionType.RAISE:
            if new_value is None:
                return False

            if (new_value < self.big_blind and action != ActionType.ALL_IN) or \
               player_amount + self.players[id].chips < new_value:
                return False

            return True
        elif new_action == ActionType.FOLD:
            return True
        else:
            return False

    def _safe_execute(self, id: int, action: ActionType, value: Optional[int] = None) -> bool:
        """
        Safely execute the potentially invalid action for the given player.

        Arguments:
            id (int) 				- the player to take action
            action (ActionType) 	- The ActionType to take
            value (Optional[int]) - In the case of raise, how much to raise
        Returns:
            bool - True if successfully executed, False otherwise
        """
        # Validate move
        if not self.validate_move(id, action, value):
            return False

        # ALL_IN should be translated
        if action == ActionType.ALL_IN:
            action, value = self._translate_allin(action, value)

        player_amount = self.player_bet_amount(id)
        chips_to_call = self.chips_to_call(id)

        # Execute move
        if action == ActionType.CALL:
            self._player_post(id, chips_to_call)
        elif action == ActionType.CHECK:
            pass
        elif action == ActionType.RAISE:
            self._player_post(id, value - player_amount)
        elif action == ActionType.FOLD:
            self.players[id].state = PlayerState.OUT
            for i in range(self.players[id].last_pot + 1):
                self.pots[i].remove_player(id)
        else:
            return False

        return True

    def _translate_allin(self, action: ActionType, value: int = None) -> Tuple[ActionType, Optional[int]]:
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

    def _betting_round(self) -> Iterator[TexasHoldEm]:
        """
        Core round of the poker game. Executes actions from each active player
        until everyone "checks"

        Raises:
            PokerError - If self.hand_state is not a valid betting round
        """

        if self.hand_phase == HandPhase.PREHAND or \
                self.hand_phase == HandPhase.SETTLE:
            raise PokerError("Not valid betting round!")

        first_pot = self.get_last_pot_id()
        player_iter = self.in_pot_iter(self.current_player)

        while not self._is_hand_over():
            try:
                self.current_player = next(player_iter)
            except StopIteration:
                break

            yield self

            action, val = self._translate_allin(*self.action)
            passed = self._safe_execute(self.current_player, action, val)

            if not passed:
                raise PokerError(f"Invalid move for player {self.current_player}: "
                                 f"{action}, {val}")

            if self.hand_phase not in self.hand_history:
                self.hand_history[self.hand_phase] = BettingRoundHistory(actions=[])
            betting_history = self.hand_history.get(self.hand_phase)
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
            self.get_pot(i).collect_bets()

    def get_hand(self, player_id) -> list[Card]:
        """
        Arguments:
            player_id (int): The ID of the player
        Returns:
            list[Card]: A two element list of the hand of the given player,
                if player has not been dealt a hand, returns an empty list

        """
        return self.hands.get(player_id, [])

    def set_action(self, action_type: ActionType, val: Optional[int] = None):
        if not self.is_hand_running():
            raise PokerError("Cannot set action, hand is not running.")
        self.action = (action_type, val)

    def run_hand(self) -> Iterator[TexasHoldEm]:
        """
        Runs a complete hand of the game.

        Returns:
            (Iterator[TexasHoldEm])	- A generator over every intermediate game state.
                                      i.e. right before the first action, right after
                                      every action, and right after settlement.
        """
        if self.is_hand_running():
            raise PokerError('In the middle of a hand!')

        self.hand_phase = HandPhase.PREHAND
        next(self._handstate_handler[self.hand_phase]())

        if self.game_state == GameState.STOPPED:
            return

        self.hand_phase = self.hand_phase.next_phase()
        while self.is_hand_running():
            yield from self._handstate_handler[self.hand_phase]()

            if self._is_hand_over():
                self.hand_phase = HandPhase.SETTLE
                yield from self._handstate_handler[self.hand_phase]()
                self.hand_phase = self.hand_phase.next_phase()
                break
            else:
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
