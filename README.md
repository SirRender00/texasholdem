# texasholdem
A python package for Texas Hold 'Em Poker.

Latest Stable Release Version: v0.4.5 \
[Changelog](https://github.com/SirRender00/texasholdem/releases/tag/v0.4.5) \
[Documentation](https://texasholdem.readthedocs.io/en/latest/)

Latest Experimental Release Version v0.5-alpha.1 \
[Changelog](https://github.com/SirRender00/texasholdem/releases/tag/v0.5-alpha.1) \
[Documentation](https://texasholdem.readthedocs.io/en/latest/)

Roadmap \
[v1.0.0](https://github.com/SirRender00/texasholdem/wiki/Version-1.0.0-Roadmap)

## Contributing
To be added as a contributor, please email me at evyn.machi@gmail.com with your GitHub username and mention one of the open issues / a new issue you would like to tackle first.
For more information about contributing, please see the wiki.

## Install
```bash
pip install texasholdem
```

## Quickstart
Playing a game from the command line is as simple as the following:
```python
from texasholdem import TexasHoldEm
from texasholdem.gui import TextGUI

game = TexasHoldEm(buyin=500,
                   big_blind=5,
                   small_blind=2,
                   max_players=6)
gui = TextGUI()
gui.set_player_ids(list(range(6)))      # see all cards
while game.is_game_running():
    game.start_hand()
    while game.is_hand_running():
        gui.print_state(game)

        action, val = gui.accept_input()
        while not game.validate_move(game.current_player, action, val):
            print(f"{action} {val} is not valid for player {game.current_player}")
            action, val = gui.accept_input()

        gui.print_action(game.current_player, action, val)
        game.take_action(action, val)
```

## Overview
### Game Information
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

player_id = game.current_player
game.take_action(ActionType.RAISE, value=10)
assert game.player_bet_amount(player_id) == 10
assert game.chips_at_stake(player_id) == 20     # total amount in all pots the player is in

assert game.chips_to_call(game.current_player) == 10 - game.big_blind
```

### Cards
The card module represents cards as 32-bit integers for simple and fast hand
evaluations. For more information about the representation, see the `Card`
module.

```python
from texasholdem import Card

card = Card("Kd")                       # King of Diamonds
assert isinstance(card, int)            # True
assert card.rank == 11                  # 2nd highest rank (0-12)
assert card.pretty_string == "[ K ♦ ]"
```

### Agents
The package also comes with basic agents including `call_agent` and `random_agent`

```python
from texasholdem import TexasHoldEm
from texasholdem.agents import random_agent, call_agent

game = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)
game.start_hand()

while game.is_hand_running():
    if game.current_player % 2 == 0:
        game.take_action(*random_agent(game))
    else:
        game.take_action(*call_agent(game))
```

The `game.get_hand(player_id=...)` method of the `TexasHoldEm` class 
will return a list of type `list[Card]`.

### Game History
Export and import the history of hands:
```python
from texasholdem import TexasHoldEm
from texasholdem.gui import TextGUI

game = TexasHoldEm(buyin=500, big_blind=5, small_blind=2)
game.start_hand()

while game.is_hand_running():
    game.take_action(*some_strategy(game))

# export to file
game.export_history("./pgns/my_game.pgn")

# import and replay
gui = TextGUI()
for state in TexasHoldEm.import_history("./pgns/my_game.pgn"):
    gui.print_state(state)
```
PGN files also support single line and end of line comments starting with "#".

### Poker Evaluator
The evaluator module returns the rank of the best 5-card hand from a list of 5 to 7 cards.
The rank is a number from 1 (strongest) to 7462 (weakest). This determines the winner in the `TexasHoldEm` module:

```python
from texasholdem import Card
from texasholdem.evaluator import  evaluate, rank_to_string

assert evaluate(cards=[Card("Kd"), Card("5d")],
                board=[Card("Qd"), 
                       Card("6d"), 
                       Card("5s"), 
                       Card("2d"),
                       Card("5h")]) == 927
assert rank_to_string(927) == "Flush, King High"
```
