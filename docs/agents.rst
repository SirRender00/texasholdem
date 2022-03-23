.. _agents:

Agents
========

Agents are a relatively new feature and currently the package comes with two basic agents.
:func:`~texasholdem.agents.basic.call_agent` or :func:`~texasholdem.agents.basic.random_agent`

Agents are implemented as functions and take a game as input and output an action of the current player::

    action, total = call_agent(game)
    assert action == ActionType.CALL
    assert total == None

Basic Agents
-------------

Call Agent
^^^^^^^^^^^
The :func:`~texasholdem.agents.basic.call_agent` predictably returns a :obj:`~texasholdem.action_type.CALL` action
if anyone raised or a :obj:`~texasholdem.action_type.CHECK` action if not.

Random Agent
^^^^^^^^^^^^^
The :func:`~texasholdem.agents.basic.random_agent` chooses an action uniformly at random from the available moves.

.. note::
    This includes a :obj:`~texasholdem.action_type.FOLD` action if no one raised. To disable this you can pass in a
    :code:`no_fold=True` argument when calling it. For example, :code:`random_agent(game, no_fold=True)`.
