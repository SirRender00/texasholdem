from enum import Enum, auto


class PlayerState(Enum):
    """
    Player state Enum. For example, if a player is in the pot with the proper amount
    of chips, that player is said to be :obj:`PlayerState.IN`. If a player needs to call a bet,
    that player has status :obj:`PlayerState.TO_CALL`. If a player has no more chips to bet,
    that player is :obj:`PlayerState.ALL_IN`, etc.

    """

    SKIP = auto()
    """Player is sitting out this hand, they will not be dealt
    cards and will rejoin upon request. Will be implemented in a future version."""

    OUT = auto()
    """Player has folded their hand this round."""

    IN = auto()
    """Player is in the latest pot and has put in enough chips."""

    TO_CALL = auto()
    """Player is in the latest pot and needs to call a raise."""

    ALL_IN = auto()
    """Player is all-in and cannot take more actions this hand."""
