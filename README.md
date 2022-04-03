# texasholdem
![Pytest Status](https://github.com/SirRender00/texasholdem/actions/workflows/pytest.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://raw.githubusercontent.com/SirRender00/texasholdem/main/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/texasholdem/badge/?version=stable)](https://texasholdem.readthedocs.io/en/stable/?badge=stable)
![Pylint Status](https://github.com/SirRender00/texasholdem/actions/workflows/pylint.yml/badge.svg)

A python package for Texas Hold 'Em Poker.

Latest Stable Release Version: v0.6.3 \
[Changelog](https://github.com/SirRender00/texasholdem/releases/tag/v0.6.3) \
[Documentation](https://texasholdem.readthedocs.io/en/stable/)

Latest Experimental Release Version v0.6.3 \
[Changelog](https://github.com/SirRender00/texasholdem/releases/tag/v0.6.3) \
[Documentation](https://texasholdem.readthedocs.io/en/latest/)

Roadmap \
[v1.0.0](https://github.com/SirRender00/texasholdem/wiki/Version-1.0.0-Roadmap)

## Contributing
Want a new feature, found a bug, or have questions? Feel free to add to our issue board on Github!
[Open Issues](https://github.com/SirRender00/texasholdem/issues>).

We welcome any developer who enjoys the package enough to contribute! Please message me at evyn.machi@gmail.com
if you want to be added as a contributor and check out the 
[Developer's Guide](https://github.com/SirRender00/texasholdem/wiki/Developer's-Guide).

## Install
The package is available on pypi and can be installed with

```bash
pip install texasholdem
```

For the latest experimental version
```bash
pip install texasholdem --pre
```

## Quickstart
Play a game from the command line and take turns for every player out of the box.

```python
from texasholdem.game.game import TexasHoldEm
from texasholdem.gui.text_gui import TextGUI

game = TexasHoldEm(buyin=500, big_blind=5, small_blind=2, max_players=6)
gui = TextGUI(game=game)

while game.is_game_running():
    game.start_hand()

    while game.is_hand_running():
        gui.run_step()

    path = game.export_history('./pgns')     # save history
    gui.replay_history(path)                 # replay history
```

## Overview
The following is a quick summary of what's in the package. Please see the 
[docs](https://texasholdem.readthedocs.io/en/stable/) for all the details.

### Game Information

Get game information and take actions through intuitive attributes.

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
assert len(game.get_hand(game.current_player)) == 2

game.take_action(ActionType.CALL)

player_id = game.current_player
game.take_action(ActionType.RAISE, total=10)
assert game.player_bet_amount(player_id) == 10
assert game.chips_at_stake(player_id) == 20     # total amount in all pots the player is in

assert game.chips_to_call(game.current_player) == 10 - game.big_blind
```

### Cards
The card module represents cards as 32-bit integers for simple and fast hand
evaluations.

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

### Game History
Export and import the history of hands to files.

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
The rank is a number from 1 (strongest) to 7462 (weakest).

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

### GUIs
The GUI package currently comes with a text-based GUI to play games from the command line. Coming later
will be web-app based GUIs.
