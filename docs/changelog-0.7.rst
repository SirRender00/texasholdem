Changes in 0.7.0
==========================

What's New in 0.7
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
