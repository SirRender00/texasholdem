from enum import Enum, auto


class ActionType(Enum):
    """An enum representing the types of actions a player can take."""

    RAISE = auto()
    """Raises the latest pot."""

    ALL_IN = auto()
    """Posts all available chips to the current pot."""

    CALL = auto()
    """Posts the minimum chips to remain in the pot."""

    CHECK = auto()
    """Passes the action."""

    FOLD = auto()
    """Folds the hand and exits the pot."""
