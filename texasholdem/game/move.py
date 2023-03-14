"""
The move module includes classes related to collections of moves
"""
import random
from typing import Dict, Tuple, Optional, Union, List
from collections.abc import Sequence
import warnings

from deprecated.sphinx import versionadded

from texasholdem.game.action_type import ActionType


@versionadded(version="0.9.0")
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

        self._action_types = list(
            sorted(moves.keys(), key=tuple(ActionType).index, reverse=True)
        )

    def __contains__(self, item) -> bool:
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

    def __len__(self) -> int:
        return len(self._action_types) + len(self._raise_range) - 1

    def __getitem__(self, item: int) -> ActionType:
        if item < len(self._action_types):
            return self._action_types[item], None
        if not self._raise_range:
            raise IndexError
        if item < len(self):
            return ActionType.RAISE, self._raise_range[item - len(self._action_types)]
        raise IndexError

    def __delitem__(self, key) -> None:
        if isinstance(key, ActionType):
            if key in self._action_types:
                self._action_types.__delitem__(key)
            elif key == ActionType.RAISE:
                if key not in self._raise_range:
                    raise KeyError
                self._raise_range = range(0)
        raise KeyError

    def __repr__(self) -> str:
        move_dict = {move: None for move in self._action_types}
        if self._raise_range:
            move_dict[ActionType.RAISE] = self._raise_range
        return self.__class__.__name__ + f"({repr(move_dict)})"

    def __str__(self) -> str:
        return repr(self)

    @property
    def action_types(self) -> List[ActionType]:
        """
        Returns:
            List[ActionType]: A list of action types represented
        """
        return self._action_types

    @property
    def raise_range(self) -> range:
        """
        The range of the represented raise action, if no raise is possible this is just range(0)

        Returns:
            range: The range of the represented raise action.
        """
        return self._raise_range

    def sample(
        self, num=1
    ) -> Union[
        Tuple[ActionType, Optional[int]], List[Tuple[ActionType, Optional[int]]]
    ]:
        """
        Arguments:
            num (int): The number of samples
        Returns:
            Union[Tuple[ActionType, Optional[int]], List[Tuple[ActionType, Optional[int]]]]:
                The sample(s) of action, total tuples
        """
        action_types = random.choices(self.action_types, k=num)
        if ActionType.RAISE in self:
            totals = random.choices(self.raise_range, k=num)
            totals = [
                totals[i] if action_types[i] == ActionType.RAISE else None
                for i in range(num)
            ]
        else:
            totals = [None for _ in range(num)]

        samples = list(zip(action_types, totals))
        if num == 1:
            return samples[0]
        return samples
