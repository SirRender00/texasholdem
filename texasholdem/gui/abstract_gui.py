import abc
import os
import logging
from typing import Optional, Iterable, Tuple, Union

from deprecated.sphinx import versionadded

from texasholdem.game.action_type import ActionType
from texasholdem.game.game import TexasHoldEm


logger = logging.getLogger(__name__)


class AbstractGUI(abc.ABC):
    """
    This class provides a recommended outline of the methods that every TexasHoldEm GUI
    should implement. It also comes with a few convenience methods for implementations,
    including :meth:`run_step` which runs a complete step of the game (display state,
    take input, show state, etc.) and :meth:`replay_history` which allows the user
    to step through the given history.

    Arguments:
        game (TexasHoldEm, optional): The game object to attach to, all methods will
            default to this game. (Not necessary if only showing the history)
        visible_players (Iterable[int], optional): The players whose cards should be
            displayed whenever the :meth:`display_state` method is called, defaults to every
            player.
        enable_animation (bool): If set to True, will play animations, default True.
        no_wait (bool): If set to True, disables waiting mechanisms and will not block.
    Attributes:
        game (TexasHoldEm, optional): The game object to attach to, all methods will
            default to this game. (Not necessary if only showing the history)
        visible_players (list[int], optional): The players whose cards should be displayed
            whenever the :meth:`display_state` method is called, defaults to every player.
        enable_animation (bool): If set to True, will play animations, default True.
        no_wait (bool): If set to True, disables waiting mechanisms and will not block.

    """

    def __init__(
        self,
        game: Optional[TexasHoldEm] = None,
        visible_players: Optional[Iterable[int]] = None,
        enable_animation: bool = True,
        no_wait: bool = False,
    ):
        self.game = game
        self.visible_players = visible_players
        self.no_wait = no_wait
        self.enable_animation = enable_animation

        # All players visible by default
        if visible_players is None and game:
            self.set_visible_players(range(self.game.max_players))

    @versionadded(version="0.7.0")
    def set_visible_players(self, visible_players: Iterable[int]):
        """
        Make the given players' cards visible.

        Arguments:
            visible_players (Iterable[int]): The players whose cards should be visible when the
                :meth:`display_state` method is called.
        Raises:
            ValueError: If any of the player ids given are invalid.

        """
        if not visible_players:
            self.visible_players = visible_players
            return

        sorted_players = sorted(list(visible_players))
        if len(sorted_players) > self.game.max_players:
            raise ValueError(
                "Expected length of visible players to be <= number of players. "
                f"Expected <= {self.game.max_players}, Got {len(sorted_players)}."
            )

        for player_id, criteria in (
            (sorted_players[0], lambda i: i < 0),
            (sorted_players[-1], lambda i: i > self.game.max_players - 1),
        ):
            if criteria(player_id):
                raise ValueError(f"Unexpected player id {player_id}")

        self.visible_players = sorted_players

    @versionadded(version="0.7.0")
    def prompt_input(self):
        """
        Prompt the user for input.

        """

    @versionadded(version="0.7.0")
    def accept_input(self) -> Tuple[ActionType, Optional[int]]:
        """
        Receive input from the user and translate the given input to the canonical
        (ActionType, int) tuple form.

        Implementations should only focus on this direct translation and not worry about
        validating the move with respect to the game. Implementations should also raise a
        ValueError if the given user input is malformed.

        Returns:
            Tuple[ActionType, Optional[int]]: The action
        Raises:
            ValueError: If the given input could not be parsed

        """
        raise NotImplementedError()

    @versionadded(version="0.7.0")
    def hide(self):
        """
        Hide the GUI.

        """
        raise NotImplementedError()

    @versionadded(version="0.7.0")
    def refresh(self):
        """
        Refresh the GUI.

        """

    @versionadded(version="0.7.0")
    def wait_until_prompted(self):
        """
        Wait until the user gives the appropriate signal.

        """

    @versionadded(version="0.7.0")
    def display_state(self):
        """
        Display the state of the game.

        """
        raise NotImplementedError()

    @versionadded(version="0.7.0")
    def display_error(self, error: str):
        """
        Display any potential errors from users (malformed input, invalid action, etc.)

        Arguments:
            error (str): The error message

        """

    @versionadded(version="0.7.0")
    def display_action(self):
        """
        Display the most recent action

        """

    @versionadded(version="0.7.0")
    def display_win(self):
        """
        Display the winners of the hand, (and everyone's cards that didn't fold)

        """
        raise NotImplementedError()

    @versionadded(version="0.7.0")
    def run_step(self):
        """
        Runs a complete GUI step of the hand:

            - Display the game state
            - Prompt for action from the user until valid
            - Take the action and display it
            - Display the winners if the hand ended

        This is included as a convenience method built from the other necessary
        abstract methods.

        """
        if not self.game.is_hand_running():
            return

        self.display_state()

        # Prompt for action input until valid
        while True:
            try:
                self.prompt_input()
                action, total = self.accept_input()
                self.game.validate_move(action=action, total=total, throws=True)
                break
            except ValueError as err:
                logger.warning("Caught error: %s.", str(err), exc_info=err)
                self.display_error(str(err))

        # Take the action in the game
        self.game.take_action(action, total=total)

        # Announce the move
        self.display_action()

        # display game after running action
        self.display_state()

        # Display the winners if the hand ended
        if not self.game.is_hand_running():
            self.display_win()

    @versionadded(version="0.7.0")
    def replay_history(self, path: Union[str, os.PathLike]):
        """
        Replays the given history, going forward when prompted.

        This is included as a convenience method built from the other necessary
        abstract methods.

        """
        old_game = self.game
        old_visible_players = self.visible_players

        for state in TexasHoldEm.import_history(path):
            self.game = state
            self.set_visible_players(range(self.game.max_players))
            self.refresh()
            self.display_action()
            self.display_state()
            self.wait_until_prompted()

        self.game = old_game
        self.visible_players = old_visible_players
