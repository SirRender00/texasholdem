from __future__ import annotations

from enum import Enum
from dataclasses import dataclass


@dataclass(frozen=True)
class _HandPhase:
    """
    Hand phase
    """
    new_cards: int
    next_phase: str


class HandPhase(Enum):
    """An enum representing the phases of each hand which includes the well-known

        - :obj:`HandPhase.PREFLOP`
        - :obj:`HandPhase.FLOP`
        - :obj:`HandPhase.TURN`
        - :obj:`HandPhase.RIVER`

    In addition to two new phases

        - :obj:`HandPhase.PREHAND`
        - :obj:`HandPhase.SETTLE`

    which are used for book-keeping.

    """

    PREHAND = _HandPhase(0, "PREFLOP")
    """
    In this phase, players sit out if requested, players
    rejoin if requested, blinds are moved and posted, and card
    are dealt.
    """

    PREFLOP = _HandPhase(0, "FLOP")
    """
    The first betting round of the game. Players have two cards with no
    communal cards yet.
    """

    FLOP = _HandPhase(3, "TURN")
    """
    The second betting round of the game. Three communal cards come outs.
    """

    TURN = _HandPhase(1, "RIVER")
    """
    The third betting round of the game. One more communal card comes out.
    """

    RIVER = _HandPhase(1, "SETTLE")
    """
    The fourth and final betting round of the game. One more communal cards come out.
    """

    SETTLE = _HandPhase(0, "PREHAND")
    """
    If the hand ended early in a previous round, the rest of the communal cards come out
    to total 5. Winners are decided per pot based on hand strength and rewarded chips.
    """

    def next_phase(self) -> HandPhase:
        """
        Returns:
            HandPhase: The next HandPhase after this one

        """
        return HandPhase[self.value.next_phase]

    def new_cards(self) -> int:
        """
        Returns:
            int: The number of new cards to add to the board

        """
        return self.value.new_cards
