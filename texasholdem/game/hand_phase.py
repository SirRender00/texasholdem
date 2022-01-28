"""The handphase module contains an enum with the possible handphases
of the game. It includes the well-known PREHAND, PREFLOP, FLOP, and RIVER
phases, in addition to new PREHAND and SETTLE phases purely for book-keeping."""

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
    """An enum representing the phase of the hand."""

    PREHAND = _HandPhase(0, "PREFLOP")
    """In this phase, players sit out if requested, players
    rejoin if requested, blinds are moved and posted, and card
    are dealt."""

    PREFLOP = _HandPhase(0, "FLOP")
    FLOP = _HandPhase(3, "TURN")
    TURN = _HandPhase(1, "RIVER")
    RIVER = _HandPhase(1, "SETTLE")

    SETTLE = _HandPhase(0, "PREHAND")
    """In this phase, the pots are settled and the last aggressor
    shows their card, while every player in turn either shows
    or folds their card."""

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
