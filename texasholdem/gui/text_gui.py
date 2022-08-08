# pylint: disable=invalid-name,too-many-lines
from __future__ import annotations
import enum
import logging
import math
import platform
import shutil
import re
import sys
from typing import Iterable, Optional, Union, Tuple, Dict, List
import curses
from collections import namedtuple, deque
import signal
from importlib.metadata import version

from deprecated.sphinx import deprecated

from texasholdem.util.errors import Ignore
from texasholdem.util.functions import preflight, handle, raise_if
from texasholdem.card import card
from texasholdem.game.game import TexasHoldEm
from texasholdem.game.action_type import ActionType
from texasholdem.game.hand_phase import HandPhase
from texasholdem.game.player_state import PlayerState
from texasholdem.gui.abstract_gui import AbstractGUI


# Windows Compatibility
_OS = platform.system()
_IS_WINDOWS = _OS == "Windows"

if _IS_WINDOWS:
    curses.resizeterm = curses.resize_term


logger = logging.getLogger(__name__)


_BlockDim = namedtuple("_BlockDim", ["rows", "cols"])


class _Ellipse:
    """
    Represents an ellipse, contains methods to
        - Get a :meth:`point_yx` from radians
        - Get the :meth:`derivative` from radians
        - Get the :meth:`char_at` radians which describes the derivative

    Arguments:
        major (float): The semi-major axis length
        minor (float): The semi-minor axis length
        center (Tuple[float, float]): The center of the ellipse

    """

    def __init__(
        self,
        major: float = None,
        minor: float = None,
        center: Tuple[float, float] = (0, 0),
    ):
        self.major = major
        self.minor = minor
        self.center = center

    def point_yx(self, rads: float) -> Tuple[float, float]:
        """
        Arguments:
            rads (float): The radians
        Returns:
            Tuple[float, float]: The point y, x

        """
        return (
            self.minor * math.sin(rads) + self.center[1],
            self.major * math.cos(rads) + self.center[0],
        )

    def derivative(self, rads: float) -> float:
        """
        Arguments:
            rads (float): The radians
        Returns:
            float: The derivative dy/dx

        """
        return (rads * self.minor * math.cos(rads)) / (
            rads * self.major * -math.sin(rads)
        )

    def char_at(self, rads: float) -> str:
        """
        Arguments:
            rads (float): The radians
        Returns:
            str: The character that describes the derivative at the point

        """
        derivative = self.derivative(rads=rads)
        if derivative < -0.5:
            return "|"
        if derivative < -0.25:
            return "/"
        if derivative < 0.25:
            if math.sin(rads) >= 0:
                return "_"
            return "‾"
        if derivative < 0.5:
            return "\\"
        return "|"


class _Align(enum.Enum):
    """
    Enum that represents the alignment in box top/middle/bottom

    """

    TOP = enum.auto()
    MIDDLE = enum.auto()
    BOTTOM = enum.auto()


class _Justify(enum.Enum):
    """
    Enum that represents how a text is justified in a box
    left, center, right.

    """

    LEFT = enum.auto()
    CENTER = enum.auto()
    RIGHT = enum.auto()


class _Block:
    """
    Core class of the Text GUI system. Wraps around the curses._CursesWindow object
    to provide helper functions that makes working with text, centering, resizing,
    erasing, and working with nested windows easier.

    Arguments:
        name (str): The name of the block element.
        window (curses._CursesWindow): The window object for this block (usually given
            from another :class:`_Block` with the :meth:`new_block` call (which
            calls :code:`curses.newwin`).
    Attributes:
        name (str): The name of the block element.
        window (curses._CursesWindow): The window object for this block (usually given
            from another :class:`_Block` or :class:`_CursesHelper` with the :meth:`new_block`
            call (which calls :code:`curses.newwin`).
        blocks (Dict[str, _Block]): a dictionary of child blocks.
        content (list, dict): The last *args, and **kwargs passed in to the :meth:`add_content`
            method. Used to refresh and save state.
        content_stack (deque): A stack of the previous contents saved with :meth:`stash_state`

    """

    def __init__(self, name: str, window: curses._CursesWindow = None):
        # pylint: disable=no-member
        self.name: str = name
        self.blocks: Dict[str, _Block] = {}
        self.window = window
        self.content_stack = deque(maxlen=10)
        self.content = None

    def _set_content_call(self, *args, **kwargs):
        self.content = (args, kwargs)

    @staticmethod
    def _pad(
        obj: Union[List[str], str],
        pad_obj: Union[List[str], str],
        padding_len: int,
        min_padding: int,
        align: _Align,
    ) -> Union[List[str], str]:
        # pylint: disable=too-many-arguments
        """
        Helper function to pad a list or string

        """
        if align == _Align.BOTTOM:
            before_padding = pad_obj * max(padding_len, min_padding)
            after_padding = pad_obj * min_padding
        elif align == _Align.MIDDLE:
            before_padding = after_padding = pad_obj * max(
                padding_len // 2, min_padding
            )
        else:
            after_padding = pad_obj * max(padding_len, min_padding)
            before_padding = pad_obj * min_padding

        return before_padding + obj + after_padding

    @handle(
        handler=lambda exc: logger.debug(str(exc), exc_info=exc), exc_type=curses.error
    )
    @preflight(
        prerun=lambda self, *args, **kwargs: self._set_content_call(*args, **kwargs)
    )
    def add_content(
        self,
        content: List[str],
        align: _Align = _Align.MIDDLE,
        justify: _Justify = _Justify.CENTER,
        border: bool = False,
        wrap_line: bool = False,
    ):
        # pylint: disable=too-many-arguments
        """
        Add the given string list to the block. Each element is placed on a new line.
        Pass in parameters to modify the alignment, justification, border, etc.

        Arguments:
            content (List[str]): The content to add to the block, each element is a
                new line.
            align (_Align): The alignment (top to bottom) for the content.
            justify (_Justify): The justification (left to right) for the content.
            wrap_line (bool): Set to True to split lines that would extend past the box
                boundary. Set to False to replace any overflow with '...'. Defaults to False
            border (bool): Set to True to add a border, default False.

        """
        self.window.erase()
        rows, cols = self.window.getmaxyx()
        border_int = 1 if border else 0

        if wrap_line:
            for i, text in enumerate(content):
                if len(text) >= cols:
                    end = cols - len(_DOTS) - 1
                    content[i] = text[:end]
                    content.insert(i + 1, text[end:])

        # align top/middle/bottom
        content = self._pad(
            obj=content,
            pad_obj=[""],
            padding_len=rows - len(content) - 1,
            min_padding=border_int,
            align=align,
        )

        # align left/center/right
        for i, text in enumerate(content):
            if len(text) >= cols:
                continue

            if justify == _Justify.RIGHT:
                align = _Align.BOTTOM
            elif justify == _Justify.CENTER:
                align = _Align.MIDDLE
            else:
                align = _Align.TOP

            content[i] = self._pad(
                obj=content[i],
                pad_obj=" ",
                padding_len=cols - len(text) - 1,
                min_padding=border_int,
                align=align,
            )

        # right out, masking with dots if too long
        for i, text in enumerate(content):
            if len(text) >= cols:
                text = text[: (cols - 1 - len(_DOTS))] + _DOTS
            text += "\n" if i != rows - 1 else ""
            self.window.addstr(text)

        # add border
        if border:
            self.window.border(*_BLOCK_BORDER)

    def stash_state(self):
        """
        Saves the current content call onto the :attr:`content_stack` and
        calls :meth:`stash_state` on any child blocks.

        """
        if self.content:
            self.content_stack.appendleft(self.content)
        for block in self.blocks.values():
            block.stash_state()

    def pop_state(self):
        """
        Pops from the :attr:`content_stack` and restores the content call and calls
        :meth:`pop_state` on any child blocks.

        .. note::
            Will be a noop if :attr:`content_stack` is empty

        """
        if self.content_stack:
            args, kwargs = self.content_stack.popleft()
            self.add_content(*args, **kwargs)
        for block in self.blocks.values():
            block.pop_state()

    @handle(
        handler=lambda exc: logger.debug(str(exc), exc_info=exc), exc_type=curses.error
    )
    def new_block(
        self, name: str, nlines: int, ncols: int, begin_y: int = 0, begin_x: int = 0
    ) -> _Block:
        # pylint: disable=too-many-arguments
        """
        Creates and returns a new block (that wraps around curses._CursesWindow). Note
        that this method is smart and so if the given block already exists, it will
        resize and move the block with the given arguments.

        Arguments:
            name (str): The name to give to the child block
            nlines (int): The number of rows to give the new block
            ncols (int): The number of columns to give to the new block
            begin_y (int): The topleft y coordinate of the block
            begin_x (int): The topleft x coordinate of the block
        Returns:
            _Block: The newly created block (or the existing block

        """

        if name in self.blocks:
            self.blocks[name].window.resize(nlines, ncols)
            self.blocks[name].window.mvwin(*self.bound_coords(begin_y, begin_x))
            return self.blocks[name]

        block = _Block(
            name=name,
            window=curses.newwin(nlines, ncols, *self.bound_coords(begin_y, begin_x)),
        )
        self.blocks[name] = block
        return block

    def get_block(self, name: str) -> Optional[_Block]:
        """
        Get the child block by name (also searches sub-children)

        Arguments:
            name (str): The block name to get
        Returns:
            Optional[_Block]: The _Block by name or None

        """
        if name in self.blocks:
            return self.blocks[name]
        for block in self.blocks.values():
            child = block.get_block(name)
            if child:
                return child
        return None

    def erase(self):
        """
        Erases the window and unsets the :attr:`content` attributes.

        .. note::
            You should call this method :code:`block.erase()` instead of
            :code:`block.window.erase()` as it does not erase the content from
            the stack.

        """
        self.content = None
        self.window.erase()

    def refresh(self):
        """
        Refreshes the block window and any child blocks.

        """
        self.window.refresh()
        for block in self.blocks.values():
            block.refresh()

    def bound_coords(self, y: int, x: int) -> Tuple[int, int]:
        """
        Ensures the given y, x will lay in the window.

        Arguments:
            y (int): The y coordinate
            x (int): The x coordinate
        Returns:
            Tuple[int, int]: The safe bounded coordinates

        """
        max_y, max_x = self.window.getmaxyx()
        y_start, x_start = self.window.getbegyx()
        return (
            min(max(y_start, y), y_start + max_y),
            min(max(x_start, x), x_start + max_x),
        )


# STRING CONSTANTS
_PROMPT = "$ "
_BLOCK_BORDER = ("|", "|", "-", "-", "+", "+", "+", "+")
_DOTS = "..."

# BLOCK DIMENSIONS
_PLAYER_BLOCK_SIZE = _BlockDim(rows=7, cols=20)
_PLAYER_BET_BLOCK_SIZE = _BlockDim(rows=1, cols=10)
_BOARD_BLOCK_SIZE = _BlockDim(rows=5, cols=50)
_PROMPT_BLOCK_SIZE = _BlockDim(rows=2, cols=35)
_ERROR_BLOCK_SIZE = _BlockDim(rows=1, cols=80)
_HISTORY_BLOCK_SIZE = _BlockDim(rows=-1, cols=28)
_ACTION_BLOCK_SIZE = _BlockDim(rows=1, cols=2)
_VERSION_BLOCK_SIZE = _BlockDim(rows=1, cols=25)

# OFFSETS & SIZE MULTIPLIERS
_HISTORY_BLOCK_SIZE_FACTOR = 0.95
_TABLE_ELLIPSE_OFFSET = (-15, -2)
_PLAYER_ELLIPSE_SIZE_FACTOR = 0.72
_TABLE_ELLIPSE_SIZE_FACTOR = 0.5
_PLAYER_BET_ELLIPSE_SIZE_FACTOR = 0.35
_TABLE_STEPS_RESOLUTION = 400

# KEY STROKES
_BACKSPACE = 127 if not _IS_WINDOWS else 8
_NEWLINE = 10
_RESIZE = -1
_CTRL_C = 3  # Windows Only

# ANIMATION TIMING
_ACTION_STEPS = 10
_ACTION_SLEEP_MS = 20 if not _IS_WINDOWS else 10


class TextGUI(AbstractGUI):
    """
    Text-based GUI. Play Texas Hold 'Em on the command line.

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
        visible_players (Iterable[int], optional): The players whose cards should be
            displayed whenever the :meth:`display_state` method is called, defaults to every
            player.
        enable_animation (bool): If set to True, will play animations, default True.
        no_wait (bool): If set to True, disables waiting mechanisms and will not block.

    """

    _action_patterns = (
        (r"^all(\-|\s|_)?in$", ActionType.ALL_IN),
        (r"^call$", ActionType.CALL),
        (r"^check$", ActionType.CHECK),
        (r"^fold$", ActionType.FOLD),
        (r"^raise (to )?([0-9]+)$", ActionType.RAISE),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._command_patterns = ((r"^exit|quit$", self._exit_handler),)

        # init curses
        self.main_block = _Block(name="Main Window", window=curses.initscr())

        # handle resize gracefully
        if not _IS_WINDOWS:
            signal.signal(
                signal.SIGWINCH,
                lambda signals, frame: (self.refresh(), self.main_block.window.getch()),
            )

        # cleanup before exit
        signal.signal(signal.SIGINT, lambda signals, frame: self._exit_handler())

        # hide screen until called
        if self.game:
            self.refresh()
        self.hide()

    def _exit_handler(self):
        """
        Exit handler snippet
        """
        self.hide()
        sys.exit(2)

    @deprecated(
        version="0.7.0",
        reason="Use the :meth:`set_visible_players` method instead. "
        "This function will be removed in version 1.0.0.",
    )
    def set_player_ids(self, ids: Iterable[int]):
        """
        Make the given players' cards visible.

        Arguments:
            ids (Iterable[int]): The players whose cards should be visible when the
                :meth:`display_state` method is called.

        """
        self.visible_players = list(ids)

    @deprecated(
        version="0.7.0",
        reason="Use the :meth:`display_action` method instead. "
        "This function will be removed in version 1.0.0.",
    )
    def print_action(self, id: int, action: ActionType, val: Optional[int] = None):
        # pylint: disable=redefined-builtin,unused-argument
        """
        Display the most recent action

        """
        self._display_action(player_id=id, action=action)

    @deprecated(
        version="0.7.0",
        reason="Use the :meth:`display_state` method instead. "
        "This function will be removed in version 1.0.0.",
    )
    def print_state(self, poker_game: TexasHoldEm):
        """
        Display the state of the game.

        """
        self.game = poker_game
        self.refresh()
        return self.display_state()

    def _capture_string(self) -> str:
        """
        Helper function for the :meth:`accept_input` method. Captures an inputed
        string and handles backspaces, newlines, resize key strokes, etc.

        Returns:
            str: The captured string ended by a newline
        """
        rows, _ = self.main_block.window.getmaxyx()
        string = ""
        i = len(_PROMPT)
        while True:
            ord_ = self.main_block.window.getch(rows - 1, i)

            if ord_ == _BACKSPACE:
                # Delete the backspace char
                self.main_block.window.delch(rows - 1, i + 1)
                self.main_block.window.delch(rows - 1, i)

                # Don't delete the prompt
                if i <= len(_PROMPT):
                    continue

                # delete the previous char
                self.main_block.window.delch(rows - 1, i - 1)
                i -= 1
                string = string[:-1]

            # stop string collection on newline
            elif ord_ == _NEWLINE:
                break

            # Windows Compatibility, need a workaround for SIGINT
            # For now, allow users to ctrl+c in the input phase
            elif _IS_WINDOWS and ord_ == _CTRL_C:
                self._exit_handler()

            # add to the string
            else:
                i += 1

                try:
                    string += chr(ord_)
                except ValueError as err:
                    # fail silently (don't want to echo) but preserve
                    # stack trace
                    raise Ignore() from err

        return string.strip()

    @preflight(prerun=lambda self: self.refresh())
    def accept_input(self) -> Tuple[ActionType, Optional[int]]:
        curses.echo(True)
        curses.curs_set(1)

        string = self._capture_string()

        curses.echo(False)
        curses.curs_set(0)

        self.main_block.get_block("INPUT").erase()
        self.main_block.refresh()

        string = string.lower().strip()

        # empty string noop
        if not string:
            raise Ignore()

        # special functions
        for pattern, func in self._command_patterns:
            if re.match(pattern, string):
                func()
                raise Ignore()

        # actions
        for pattern, action_type in self._action_patterns:
            match = re.match(pattern, string)

            if match:
                total = None
                if action_type == ActionType.RAISE:
                    total = int(match.group(2))

                # erase any errors
                self.main_block.get_block("ERROR").erase()

                return action_type, total

        raise ValueError(f"Could not parse '{string}'")

    def _recalculate_object_blocks(self):
        """
        Recalculates every block location and places them there
        (does not fill with with content, only places them)

        """
        rows, cols = self.main_block.window.getmaxyx()

        # Place input box on the bottom left
        self.main_block.new_block(
            "INPUT", *_PROMPT_BLOCK_SIZE, (rows - _PROMPT_BLOCK_SIZE[0]), 0
        )
        input_size = self.main_block.get_block("INPUT").window.getmaxyx()

        # Place error box on the bottom left right above the input
        self.main_block.new_block(
            "ERROR",
            *_ERROR_BLOCK_SIZE,
            (rows - input_size[0] - _ERROR_BLOCK_SIZE[0]),
            0,
        )

        player_ellipse = _Ellipse(
            major=(cols / 2) * _PLAYER_ELLIPSE_SIZE_FACTOR,
            minor=(rows / 2) * _PLAYER_ELLIPSE_SIZE_FACTOR,
            center=(
                cols / 2 + _TABLE_ELLIPSE_OFFSET[0],
                rows / 2 + _TABLE_ELLIPSE_OFFSET[1],
            ),
        )
        player_bet_ellipse = _Ellipse(
            major=(cols / 2) * _PLAYER_BET_ELLIPSE_SIZE_FACTOR,
            minor=(rows / 2) * _PLAYER_BET_ELLIPSE_SIZE_FACTOR,
            center=(
                cols / 2 + _TABLE_ELLIPSE_OFFSET[0],
                rows / 2 + _TABLE_ELLIPSE_OFFSET[1],
            ),
        )

        # Place player windows in an ellipse with player 0 at the bottom of the screen
        # and continuing clockwise.
        start_rad = math.pi / 2
        rad_per_player = (2 * math.pi) / self.game.max_players
        for player_id in range(self.game.max_players):
            rad = start_rad + rad_per_player * player_id
            y, x = player_ellipse.point_yx(rad)
            self.main_block.new_block(
                f"PLAYER_INFO_{player_id}",
                *_PLAYER_BLOCK_SIZE,
                round(y) - _PLAYER_BLOCK_SIZE[0] // 2,
                round(x) - _PLAYER_BLOCK_SIZE[1] // 2,
            )

            y, x = player_bet_ellipse.point_yx(rad)
            self.main_block.new_block(
                f"PLAYER_CHIPS_{player_id}",
                *_PLAYER_BET_BLOCK_SIZE,
                round(y) - _PLAYER_BET_BLOCK_SIZE[0] // 2,
                round(x) - _PLAYER_BET_BLOCK_SIZE[1] // 2,
            )

        # Place the board and pots in the center
        self.main_block.new_block(
            "BOARD",
            *_BOARD_BLOCK_SIZE,
            (rows - _BOARD_BLOCK_SIZE[0]) // 2 + _TABLE_ELLIPSE_OFFSET[1],
            (cols - _BOARD_BLOCK_SIZE[1]) // 2 + _TABLE_ELLIPSE_OFFSET[0],
        )

        # Place history on the right
        self.main_block.new_block(
            "HISTORY",
            round(rows * _HISTORY_BLOCK_SIZE_FACTOR),
            _HISTORY_BLOCK_SIZE[1],
            rows - round(rows * _HISTORY_BLOCK_SIZE_FACTOR),
            cols - _HISTORY_BLOCK_SIZE[1],
        )

        # version block above history
        self.main_block.new_block(
            "VERSION", *_VERSION_BLOCK_SIZE, 0, cols - _VERSION_BLOCK_SIZE[1]
        )

    def _player_block(self, player_id: int) -> List[str]:
        """
        Arguments:
            player_id (int): The player id
        Returns:
            List[str]: The content for the given player

        """
        block = []

        block.extend(
            [
                f"Player {player_id}",
                f"{self.game.players[player_id].state.name}",
                f"Chips: {self.game.players[player_id].chips}",
            ]
        )

        for blind, blind_str in (
            (self.game.btn_loc, "Button"),
            (self.game.sb_loc, "Small Blind"),
            (self.game.bb_loc, "Big Blind"),
        ):
            if player_id == blind:
                block.append(blind_str)
                break

        if self.game.players[player_id].state != PlayerState.SKIP:
            in_pot = list(self.game.in_pot_iter())
            if player_id in self.visible_players or (
                self.game.hand_phase == HandPhase.SETTLE
                and len(in_pot) > 1
                and player_id in in_pot
            ):
                block.append(
                    card.card_list_to_pretty_str(self.game.get_hand(player_id))
                )
            else:
                block.append("[ * ] [ * ]")

        return block

    def _player_bet_block(self, player_id: int) -> List[str]:
        """
        Arguments:
            player_id (int): The player id
        Returns:
            List[str]: The player bet amount content

        """
        return [f"Bet: {self.game.player_bet_amount(player_id)}"]

    @staticmethod
    def _version_block() -> List[str]:
        """
        Returns:
            List[str]: The version block content

        """
        return [f"texaholdem: v{version('texasholdem')}"]

    def _history_block(self) -> List[str]:
        """
        The history block includes headers for each hand phase, action callouts
        for each player during their turn, and how many chips for winners.

        Returns:
            List[str]: The content for the history

        """
        history_rows, history_cols = self.main_block.get_block(
            "HISTORY"
        ).window.getmaxyx()
        history_rows, history_cols = (
            history_rows - 2,
            history_cols - 3,
        )  # for the border / newline
        history_border = "-" * history_cols
        block = deque(maxlen=history_rows)

        block.append(f"Hand #{self.game.num_hands}")
        for hand_phase in (
            HandPhase.PREFLOP,
            HandPhase.FLOP,
            HandPhase.TURN,
            HandPhase.RIVER,
        ):
            if hand_phase in self.game.hand_history:
                block.append(history_border)
                block.append(hand_phase.name)
                block.append(history_border)
                for action in self.game.hand_history[hand_phase].actions:
                    block.append(str(action))

        if HandPhase.SETTLE in self.game.hand_history:
            block.append(history_border)
            block.append(HandPhase.SETTLE.name)
            block.append(history_border)
            block.extend(str(self.game.hand_history[HandPhase.SETTLE]).split("\n"))

        return list(block)

    def _board_block(self) -> List[str]:
        """
        The board block includes the board cards and the pots.

        Returns:
            List[str]: The content for the board and for the pots

        """
        return [
            f"Board: {card.card_list_to_pretty_str(self.game.board)}",
            "",
            *(
                f"Pot {i}: {pot.get_amount()} ({pot.get_total_amount() - pot.get_amount()})"
                for i, pot in enumerate(self.game.pots)
            ),
        ]

    def _paint_table_ring(self):
        """
        Paints the table ellipse directly the main window.

        """
        # paint table
        rows, cols = self.main_block.window.getmaxyx()
        table_ellipse = _Ellipse(
            major=(cols / 2) * _TABLE_ELLIPSE_SIZE_FACTOR,
            minor=(rows / 2) * _TABLE_ELLIPSE_SIZE_FACTOR,
            center=(
                cols / 2 + _TABLE_ELLIPSE_OFFSET[0],
                rows / 2 + _TABLE_ELLIPSE_OFFSET[1],
            ),
        )

        for step in range(1, _TABLE_STEPS_RESOLUTION):
            rad = ((2 * math.pi) / _TABLE_STEPS_RESOLUTION) * step
            y, x = table_ellipse.point_yx(rad)
            self.main_block.window.addstr(
                *self.main_block.bound_coords(round(y), round(x)),
                table_ellipse.char_at(rad),
            )

    def refresh(self):
        """
        Refreshes the display

        """
        self.main_block.stash_state()
        self.main_block.window.clear()

        x, y = shutil.get_terminal_size()
        curses.resizeterm(y, x)

        self._paint_table_ring()
        self._recalculate_object_blocks()

        self.main_block.pop_state()
        self.main_block.refresh()

    def hide(self):
        curses.endwin()

    def display_state(self):
        # paint board
        self.main_block.blocks["BOARD"].add_content(content=self._board_block())

        # paint players
        for player_id in range(self.game.max_players):
            self.main_block.blocks[f"PLAYER_INFO_{player_id}"].add_content(
                content=self._player_block(player_id),
                border=player_id == self.game.current_player,
            )

            self.main_block.blocks[f"PLAYER_CHIPS_{player_id}"].add_content(
                content=self._player_bet_block(player_id)
            )

        # history
        self.main_block.blocks["HISTORY"].add_content(
            content=self._history_block(),
            align=_Align.BOTTOM,
            border=True,
            wrap_line=True,
        )

        # version
        self.main_block.blocks["VERSION"].add_content(content=self._version_block())
        self.main_block.refresh()

    def prompt_input(self, preamble: Optional[List[str]] = None):
        if preamble is None:
            preamble = [f"Player {self.game.current_player}'s turn"]

        self.main_block.get_block("INPUT").erase()
        self.main_block.get_block("INPUT").add_content(
            [*preamble, _PROMPT], align=_Align.BOTTOM, justify=_Justify.LEFT
        )
        self.main_block.refresh()

    def display_error(self, error: str):
        self.main_block.get_block("ERROR").erase()
        self.main_block.get_block("ERROR").add_content(
            [error], align=_Align.BOTTOM, justify=_Justify.LEFT
        )
        self.main_block.refresh()

    @handle(
        handler=lambda exc: logger.info("Skipping because animation is disabled"),
        exc_type=Ignore,
    )
    @preflight(
        prerun=lambda self, *args, **kwargs: raise_if(
            Ignore(), not self.enable_animation
        )
    )
    def _display_action(self, player_id: int, action: ActionType):
        """
        Animates the chip movement for raise and call actions.

        """
        curses.curs_set(0)

        if action in (ActionType.RAISE, ActionType.CALL):
            player_y, player_x = self.main_block.get_block(
                f"PLAYER_INFO_{player_id}"
            ).window.getbegyx()
            bet_y, bet_x = self.main_block.get_block(
                f"PLAYER_CHIPS_{player_id}"
            ).window.getbegyx()

            start_y, start_x = (
                player_y + _PLAYER_BLOCK_SIZE[0] // 2,
                player_x + _PLAYER_BLOCK_SIZE[1] // 2,
            )
            end_y, end_x = (
                bet_y + _PLAYER_BET_BLOCK_SIZE[0] // 2,
                bet_x + _PLAYER_BET_BLOCK_SIZE[1] // 2,
            )

            y, x = start_y, start_x
            tick_y, tick_x = (
                (end_y - start_y) / _ACTION_STEPS,
                (end_x - start_x) / _ACTION_STEPS,
            )

            self.main_block.new_block(
                "ACTION", *_ACTION_BLOCK_SIZE, round(y), round(x)
            ).add_content(["*"])

            while (round(y), round(x)) != (end_y, end_x):
                y += tick_y
                x += tick_x

                self.main_block.get_block("ACTION").erase()
                self.main_block.new_block(
                    "ACTION", *_ACTION_BLOCK_SIZE, round(y), round(x)
                ).add_content(["*"])
                curses.napms(_ACTION_SLEEP_MS)
                self.refresh()

            self.main_block.blocks.pop("ACTION").window.erase()

    def display_action(self):
        if not self.game.hand_history.combined_actions():
            return
        player_action = self.game.hand_history.combined_actions()[-1]
        player_id, action = player_action.player_id, player_action.action_type
        self._display_action(player_id, action)

    def display_win(self):
        old_visible_players = self.visible_players

        # in the settle phase, players going to showdown show cards
        extras = set(self.game.in_pot_iter())
        extras = (
            extras if len(extras) > 1 else []
        )  # don't out players win without contest
        self.set_visible_players(set(self.visible_players).union(extras))

        self.display_state()
        self.main_block.refresh()

        self.wait_until_prompted()

        self.visible_players = old_visible_players

    @handle(
        handler=lambda exc: logger.info("Skipping because no_wait is True"),
        exc_type=Ignore,
    )
    @preflight(prerun=lambda self: raise_if(Ignore(), self.no_wait))
    def wait_until_prompted(self):
        self.prompt_input(preamble=["Press enter to continue"])
        curses.curs_set(0)
        self.main_block.refresh()
        self.main_block.window.getstr()
