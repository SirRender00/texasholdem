"""The player state module includes an enum which represents the player
state. For example, if a player is in the pot with the proper amount
of chips, that player is said to be IN. If a player needs to call a bet,
that player has status TO_CALL. If a player has no more chips to bet,
that player is ALL_IN, etc."""

from enum import Enum, auto


class PlayerState(Enum):
    """An enum representing a player state (i.e. needs to
    call, in the pot, sitting out, etc."""

    SKIP = auto()
    """Player is sitting out this hand, they will not be dealt
    cards and will rejoin upon request."""

    OUT = auto()
    """Player has folded their hand this round."""

    IN = auto()
    """Player is in the latest pot and has put in enough chips."""

    TO_CALL = auto()
    """Player is in the latest pot and needs to call a raise."""

    ALL_IN = auto()
    """Player is all-in and cannot take more actions this hand."""
