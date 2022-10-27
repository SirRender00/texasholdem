texasholdem |release|
=======================

.. toctree::
   :hidden:

   getting_started
   game_information
   agents
   cards
   guis
   evaluator
   reference
   changelog

A python package for Texas Hold 'Em Poker, providing

    - Fast evaluation of hand strengths
    - Export & import human-readable game history
    - GUIs to view games and game history
    - Simple & complex agents
    - Compliance with World Series of Poker Official Rules
    - And more

See the source code for this version :source_code:`on github <.>`

Getting Started
-----------------
To get started see :ref:`Getting Started <getting_started>`.

Contributing
---------------
Want a new feature, found a bug, or have questions? Feel free to add to our issue board on Github!
`Open Issues <https://github.com/SirRender00/texasholdem/issues>`_.

We welcome any developer who enjoys the package enough to contribute! Please message me at evyn.machi@gmail.com
if you want to be added as a contributor and check out the
`Developer's Guide <https://github.com/SirRender00/texasholdem/wiki/Developer's-Guide>`_.

What's New in |release|
------------------------
This release features an overhaul to the GUI system and specifically the :class:`~texasholdem.gui.text_gui.TextGUI`
had a massive overhaul. See more at :ref:`guis`.

Features
^^^^^^^^^

    - Added an :class:`~texasholdem.gui.abstract_gui.AbstractGUI` class for common functionality for all GUIs.
    - The new :class:`~texasholdem.gui.text_gui.TextGUI`
        - A new history panel
        - Support any number of players 2 thru 9
        - Chip animations
        - Improved UX

Other Changes
^^^^^^^^^^^^^^^

    - Simplification of a few steps in a betting round
    - Uncaps the python dependency
