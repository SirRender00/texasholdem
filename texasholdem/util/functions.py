from typing import Callable, Any, TypeVar, Type, Tuple

from functools import wraps

_F = TypeVar("_F", bound=Callable)
_T = TypeVar("_T")
_R = TypeVar("_R")
_E = TypeVar("_E", bound=Type[Exception])


def check_raise(exc_type: Type[Exception]):
    """
    Decorator that turns a function that returns a bool and message into
    a function that returns a bool and optionally throws an error.

    Injects argument throws (bool): default False.

    Example:
        You can use the decorator like so::

            @check_raise(ValueError)
            def validate(arg1):
                return False, "test"

            validate("arg1")                # will return False
            validate("arg1", throws=True)   # will raise ValueError("test")

    Arguments:
        exc_type (Type[Exception]): The Exception type to throw.
    """

    def decorator(func: Callable[[_T], Tuple[bool, str]]) -> Callable[[_T], bool]:
        @wraps(func)
        def inner(*args, throws=False, **kwargs):
            ret, msg = func(*args, **kwargs)
            if not ret and throws:
                raise exc_type(msg)
            return ret

        return inner

    return decorator


def handle(handler: Callable[[_E], Any], exc_type: _E = Exception):
    """
    Decorator that wraps the entire function in a try-except statement
    that catches the given :code:`exc_type` and handles it with the given handler.

    Arguments:
        exc_type (Type[Exception]): The exception type to handle
        handler: Function that handles the exc_type exception

    """

    def decorator(func: _F) -> _F:
        @wraps(func)
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exc_type as exc:  # # pylint: disable=broad-except
                return handler(exc)

        return inner

    return decorator


def preflight(prerun: Callable[[_T], Any]):
    """
    Decorator that runs the given function with the same parameters of the
    decorated function beforehand.

    Arguments:
        prerun: Function that runs before the decorated function, takes the same arguments.
    """

    def decorator(func: Callable[[_T], _R]) -> Callable[[_T], _R]:
        @wraps(func)
        def inner(*args, **kwargs):
            prerun(*args, **kwargs)
            return func(*args, **kwargs)

        return inner

    return decorator


def raise_if(exc: Exception, condition: bool):
    """
    Throws the given exception if condition is True. Useful to throw errors
    in lambda statements.

    Arguments:
        exc (Exception): The exception instance to throw
        condition (bool): If true, will raise the given error

    """
    if condition:
        raise exc
