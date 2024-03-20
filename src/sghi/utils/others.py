"""Other useful utilities."""

from collections.abc import Callable
from concurrent.futures import Future
from typing import Any

from .checkers import ensure_not_none


def future_succeeded(future: Future[Any]) -> bool:
    """
    Check if a :external+python:py:class:`~concurrent.futures.Future` completed
    successfully and return ``True`` if so, or ``False`` otherwise.

    In this context, a ``Future`` is considered to have completed successfully
    if it wasn't canceled and no uncaught exceptions were raised by its callee.

    :param future: A ``Future`` instance to check for successful completion.
        This MUST not be ``None``.

    :return: ``True`` if the future completed successfully, ``False``
        otherwise.

    :raises ValueError: If ``future`` is ``None``.
    """
    ensure_not_none(future, "'future' MUST not be None.")
    return bool(
        future.done()
        and not future.cancelled()
        and future.exception() is None,
    )


def type_fqn(klass: type[Any] | Callable[..., Any]) -> str:
    """Return the fully qualified name of a type or callable.

    :param klass: A type or callable whose fully qualified name is to be
        determined. This MUST not be ``None``.

    :return: The fully qualified name of the given type/callable.

    :raises ValueError: If ``klass`` is ``None``.
    """
    ensure_not_none(klass, "'klass' MUST not be None.")
    return ".".join((klass.__module__, klass.__qualname__))
