"""
Useful validators and predicates.
"""
from collections.abc import Callable, Sized
from typing import Any, TypeVar

from sghi.typing import Comparable

# =============================================================================
# TYPES
# =============================================================================

_ST = TypeVar("_ST", bound=Sized)
_T = TypeVar("_T")


# =============================================================================
# CHECKERS
# =============================================================================


def ensure_greater_or_equal(
        value: Comparable,
        base_value: Comparable,
        message: str = "'value' must be greater than or equal to 'base_value'.",  # noqa: E501
) -> Comparable:
    """
    Check that the given value is greater that or equal to the given base
    value.

    If ``value`` is less than the given ``base_value``, then a
    :exc:`ValueError` is raised; else ``value`` is returned as is.

    :param value: The value to check for greatness or equality.
    :param base_value: The value to compare for greatness or equality against.
    :param message: An optional error message to be shown when ``value`` is not
        greater than or equal to the given ``base_value``.

    :return: ``value`` if it is greater than or equal to ``base_value``.

    :raise ValueError: If the given ``value`` is less than the given
        ``base_value``.
    """
    if not value >= base_value:
        raise ValueError(message)
    return value


def ensure_greater_than(
        value: Comparable,
        base_value: Comparable,
        message: str = "'value' must be greater than 'base_value'.",
) -> Comparable:
    """Check that the given value is greater that the given base value.

    If ``value`` is less than or equal to the given ``base_value``, then a
    :exc:`ValueError` is raised; else ``value`` is returned as is.

    :param value: The value to check for greatness.
    :param base_value: The value to compare for greatness against.
    :param message: An optional error message to be shown when ``value`` is not
        greater than the given ``base_value``.

    :return: ``value`` if it is greater than ``base_value``.

    :raise ValueError: If the given ``value`` is less than or equal to the
         given ``base_value``.
    """
    if not value > base_value:
        raise ValueError(message)
    return value


def ensure_instance_of(
        value: Any,  # noqa: ANN401
        klass: type[_T],
        message: str | None = None,
) -> _T:
    """Check that the given value is an instance of the given type.

    If ``value`` is not an instance of ``klass``, then a :exc:`TypeError` is
    raised; else ``value`` is returned as is.

    :param value: The value whose type to check.
    :param klass: The type that the value should have.
    :param message: An optional error message to show when ``value`` is not a
        subclass of ``klass``. Defaults to a generic error message when one
        isn't provided.

    :return: ``value`` if it is an instance of ``klass``.

    :raise TypeError: If ``value`` is not an instance of ``klass``.
    """
    if not isinstance(value, klass):
        from .others import type_fqn
        _message: str = message or (
            f"'value' is not an instance of '{type_fqn(klass)}'."
        )
        raise TypeError(_message)
    return value


def ensure_less_or_equal(
        value: Comparable,
        base_value: Comparable,
        message: str = "'value' must be less than or equal to 'base_value'.",
) -> Comparable:
    """Check that the given value is less than or equal the given base value.

    If ``value`` is greater than the given ``base_value``, then a
    :exc:`ValueError` is raised; else ``value`` is returned as is.

    :param value: The value to check for `smallness` or equality.
    :param base_value: The value to compare for smallness or equality against.
    :param message: An optional error message to be shown when ``value`` is not
        less than or equal to the given ``base_value``.

    :return: ``value`` if it is less than or equal to ``base_value``.

    :raise ValueError: If the given ``value`` is greater than the given
        ``base_value``.
    """
    if not value <= base_value:
        raise ValueError(message)
    return value


def ensure_less_than(
        value: Comparable,
        base_value: Comparable,
        message: str = "'value' must be less than 'base_value'.",
) -> Comparable:
    """Check that the given value is less that the given base value.

    If ``value`` is greater than or equal to the given ``base_value``; then a
    :exc:`ValueError` is raised, else ``value`` is returned as is.

    :param value: The value to check for `smallness`.
    :param base_value: The value to compare for smallness against.
    :param message: An optional error message to be shown when ``value`` is not
        less than the given ``base_value``.

    :return: ``value`` if it is less than ``base_value``.

    :raise ValueError: If the given ``value`` is greater than or equal to the
         given ``base_value``.
    """
    if not value < base_value:
        raise ValueError(message)
    return value


def ensure_not_none(
        value: _T | None,
        message: str = '"value" cannot be None.',
) -> _T:
    """Check that a given value is not ``None``.

    If ``value`` is ``None``, then a ``ValueError`` is raised; else ``value``
    is returned as is.

    :param value: The value to check.
    :param message: An optional error message to be shown when value is
        ``None``.

    :return: The given value if the value isn't ``None``.

    :raise ValueError: If the given value is ``None``.
    """
    if value is None:
        raise ValueError(message)
    return value


def ensure_not_none_nor_empty(
        value: _ST,
        message: str = '"value" cannot be None or empty.',
) -> _ST:
    """
    Check that a :class:`Sized` value is not ``None`` or empty (has a size of
    zero).

    If ``value`` is ``None`` or empty, then a ``ValueError`` is raised; else
    ``value`` is returned as is.

    :param value: The value to check.
    :param message: An optional error message to be shown when value is
        ``None`` or empty.

    :return: The given value if it isn't ``None`` or empty.

    :raise ValueError: If ``value`` is ``None`` or empty.
    """
    if len(ensure_not_none(value, message=message)) == 0:
        raise ValueError(message)
    return value


def ensure_optional_instance_of(
        value: Any,  # noqa: ANN401
        klass: type[_T],
        message: str | None = None,
) -> _T | None:
    """
    Check that the given value is ``None`` or an instance of the given type.

    If ``value`` is not ``None`` or an instance of ``klass``, then a
    :exc:`TypeError` is raised; else ``value`` is returned as is.

    :param value: The value whose type to check.
    :param klass: The type that the value should have when not ``None``.
    :param message: An optional error message to show when ``value`` is not
        ``None`` or a subclass of ``klass``. Defaults to a generic error
        message when one isn't provided.

    :return: ``value`` if it is ``None`` or an instance of ``klass``.

    :raise TypeError: If ``value`` is not ``None`` or an instance of ``klass``.
    """
    if not isinstance(value, type(None) | klass):
        from .others import type_fqn
        _message: str = message or (
            f"'value' is not an instance of '{type_fqn(klass)}' or None."
        )
        raise TypeError(_message)
    return value


def ensure_predicate(
        test: bool,
        message: str = "Invalid value. Predicate evaluation failed.",
        exc_factory: Callable[[str], BaseException] = ValueError,
) -> None:
    """Check that a predicate evaluation passes.

    If the predicate evaluates to ``True``, then the function returns silently;
    else an exception is raised.

    :param test: An expression that applies a predicate. Should evaluate to
        ``True`` if the evaluation was successful or ``False`` otherwise.
    :param message: An optional error message to show in the raised exception
        if the predicate evaluation fails. A default error message will be used
        if none is provided.
    :param exc_factory: An optional callable that takes a string; the error
        message, and returns an appropriate exception instance. This will only
        be called if the predicate evaluation fails. Defaults to a factory that
        returns instances of ``ValueError``.

    :return: None.
    :raises BaseException: If the predicate evaluation fails. The exact
        exception type raised is determined by the ``exc_factory`` parameter.
    """
    if not test:
        raise exc_factory(message)
