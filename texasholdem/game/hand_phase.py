"""The handphase module contains an enum with the possible handphases
of the game. It includes the well-known PREHAND, PREFLOP, FLOP, and RIVER
phases, in addition to new PREHAND and SETTLE phases purely for book-keeping."""

from __future__ import annotations

from enum import Enum, auto


class HandPhase(Enum):
    """An enum representing the phase of the hand."""

    PREHAND = auto()
    """In this phase, players sit out if requested, players
    rejoin if requested, blinds are moved and posted, and card
    are dealt."""

    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()

    SETTLE = auto()
    """In this phase, the pots are settled and the last aggressor
    shows their card, while every player in turn either shows
    or folds their card."""

    def next_phase(self) -> HandPhase:
        """
        Returns:
            HandPhase: The next HandPhase after this one
        """
        return _next_phase_dict[self]


_next_phase_dict = {
    HandPhase.PREHAND: HandPhase.PREFLOP,
    HandPhase.PREFLOP: HandPhase.FLOP,
    HandPhase.FLOP: HandPhase.TURN,
    HandPhase.TURN: HandPhase.RIVER,
    HandPhase.RIVER: HandPhase.SETTLE,
    HandPhase.SETTLE: HandPhase.PREHAND
}
