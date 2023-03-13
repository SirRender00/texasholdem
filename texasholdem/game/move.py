"""
The move module includes classes related to collections of moves
"""

from typing import Dict, Tuple, Optional
from collections.abc import Sequence
import warnings

from texasholdem.game.action_type import ActionType


class MoveIterator(Sequence):
    """
    Arguments:
        moves (Dict[ActionType, Optional[range]): a dictionary from ActionType to Optional[range]
            where most of the values will be None with the ActionType.RAISE action having a range
            as a value.
    """

    def __init__(self, moves: Dict[ActionType, Optional[range]]):
        self._raise_range = range(0)
        if ActionType.RAISE in moves:
            self._raise_range = moves[ActionType.RAISE]

        self._action_types = list(sorted(moves.keys(), key=tuple(ActionType).index))

    def __contains__(self, item):
        if isinstance(item, ActionType):
            return item in self._action_types
        if isinstance(item, Tuple):
            action, maybe_val = item
            if not isinstance(action, ActionType):
                return False
            if action == ActionType.RAISE:
                if isinstance(maybe_val, float) and not maybe_val.is_integer():
                    warnings.warn("An integer was expected for value, got a float.")
                    return False
                if isinstance(maybe_val, int) or (
                    isinstance(maybe_val, float) and maybe_val.is_integer()
                ):
                    return maybe_val in self._raise_range
        if isinstance(item, int):
            return super().__contains__(item)
        return False

    def __len__(self):
        return len(self._action_types) + len(self._raise_range) - 1

    def __getitem__(self, item: int):
        if item < len(self._action_types):
            return self._action_types[item], None
        if not self._raise_range:
            raise IndexError
        if item < len(self):
            return ActionType.RAISE, self._raise_range[item - len(self._action_types)]
        raise IndexError

    def __delitem__(self, key):
        if isinstance(key, ActionType):
            if key in self._action_types:
                self._action_types.__delitem__(key)
            elif key == ActionType.RAISE:
                if key not in self._raise_range:
                    raise KeyError
                self._raise_range = range(0)
        raise KeyError

    def __repr__(self):
        move_dict = {move: None for move in self._action_types}
        if self._raise_range:
            move_dict[ActionType.RAISE] = self._raise_range
        return self.__class__.__name__ + f"({repr(move_dict)})"

    def __str__(self):
        return repr(self)

    @property
    def action_types(self):
        """
        Returns:
            List[ActionType]: A list of action types represented
        """
        return self._action_types

    @property
    def raise_range(self):
        """
        The range of the represented raise action, if no raise is possible this is just range(0)

        Returns:
            range: The range of the represented raise action.
        """
        return self._raise_range
