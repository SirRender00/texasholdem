from functools import wraps


def check_raise(exc_type: type(Exception)):
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
        exc_type (type(Exception)): The Exception type to throw.
    """

    def decorator(func):

        @wraps(func)
        def inner(*args, throws=False, **kwargs):
            ret, msg = func(*args, **kwargs)
            if not ret and throws:
                raise exc_type(msg)
            return ret

        return inner

    return decorator
