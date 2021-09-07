# texasholdem
A python package for Texas Hold 'Em Poker.

## Quickstart Guide
Starting a game is as simple as the following:
```python
from texasholdem import TexasHoldEm

game = TexasHoldEm(buyin=500, 
                   big_blind=5, 
                   small_blind=2,
                   max_players=9)
game.start_hand()
while game.is_hand_running():
    game.take_action(...)
```

## Game Information
Get game information and take actions through intuitive attributes:
```python
from texasholdem import TexasHoldEm, HandPhase, ActionType

game = TexasHoldEm(buyin=500, 
                   big_blind=5, 
                   small_blind=2,
                   max_players=9)
game.start_hand()

assert game.hand_phase == HandPhase.PREFLOP
assert HandPhase.PREFLOP.next_phase() == HandPhase.FLOP
assert game.chips_to_call(game.current_player) == game.big_blind

game.take_action(ActionType.CALL)
game.take_action(ActionType.RAISE, value=10)

assert game.chips_to_call(game.current_player) == 10 - game.big_blind
```

## Card Module
The card module represents cards as 32-bit integers for simple and fast hand
evaluations. For more information about the representation, see the `Card`
module.

```python
from texasholdem.card import Card

card = Card("Kd")                       # King of Diamonds
assert isinstance(card, int)            # True
assert card.rank == 11                  # 2nd highest rank (0-12)
assert card.pretty_string == "[ K ♦ ]"
```

The `game.get_hand(player_id=...)` method of the `TexasHoldEm` class 
will return a list of type `list[Card]`.

## Evaluator Module
The evaluator module returns the rank of the best 5-card hand from a list of 5 to 7 cards.
The rank is a number from 1 (strongest) to 7462 (weakest). This determines the winner in the `TexasHoldEm` module:

```python
from texasholdem.card import Card
from texasholdem.evaluator import evaluate, rank_to_string

assert evaluate(cards=[Card("Kd"), Card("5d")],
                board=[Card("Qd"), 
                       Card("6d"), 
                       Card("5s"), 
                       Card("2d"),
                       Card("5h")]) == 927
assert rank_to_string(927) == "Flush, King High"
```

## Development
We use python poetry for development make sure you have poetry installed.
To install all dependencies run the following from the root project directory:
```bash
poetry install
poetry update
```
