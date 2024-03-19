from typing import TYPE_CHECKING

import pytest

import sghi.app
from sghi.config import Config, ConfigProxy
from sghi.utils import (
    ensure_greater_or_equal,
    ensure_greater_than,
    ensure_instance_of,
    ensure_less_or_equal,
    ensure_less_than,
    ensure_not_none,
    ensure_not_none_nor_empty,
    ensure_optional_instance_of,
    ensure_predicate,
    type_fqn,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from sghi.typing import Comparable


def test_ensure_greater_or_equal_return_value_on_valid_input() -> None:
    """
    :func:`ensure_greater_or_equal` should return the input value if the given
    ``value`` is greater than or equal to the given ``base_value``.
    """
    assert ensure_greater_or_equal(1, 0) == 1
    assert ensure_greater_or_equal(2, 2) == 2
    assert ensure_greater_or_equal(0, -1) == 0
    assert ensure_greater_or_equal(-1, -1) == -1
    assert ensure_greater_or_equal(-0.0, -1.0) == 0.0
    assert ensure_greater_or_equal(-0.0, 0.0) == 0.0
    assert ensure_greater_or_equal(0.999999, 0) == 0.999999
    assert ensure_greater_or_equal(-19, -30) == -19


def test_ensure_greater_or_equal_fails_on_invalid_input() -> None:
    """
    :func:`ensure_greater_or_equal` raises ``ValueError`` when the given
    ``value`` is not greater than or equal to the given ``base_value``.
    """
    inputs: Iterable[tuple[Comparable, Comparable]] = (
        (0, 1),
        (-1, 0),
        (-1.0, -0.0),
        (0, 0.999999),
        (-30, -19),
    )
    # With default message
    default_msg: str = "'value' must be greater than or equal to 'base_value'."
    for value, base_value in inputs:
        with pytest.raises(ValueError, match="be greater than") as exp_info:
            ensure_greater_or_equal(value, base_value)

        assert exp_info.value.args[0] == default_msg

    # Test with a custom message
    for value, base_value in inputs:
        message: str = f"{value} must be greater than or equal to {base_value}"
        with pytest.raises(ValueError, match="be greater than") as exp_info:
            ensure_greater_or_equal(value, base_value, message=message)

        assert exp_info.value.args[0] == message


def test_ensure_greater_than_return_value_on_valid_input() -> None:
    """
    :func:`ensure_greater_than` should return the input value if the given
    ``value`` is greater than the given ``base_value``.
    """
    assert ensure_greater_than(1, 0) == 1
    assert ensure_greater_than(0, -1) == 0
    assert ensure_greater_than(-0.0, -1.0) == 0.0
    assert ensure_greater_than(0.999999, 0) == 0.999999
    assert ensure_greater_than(-19, -30) == -19


def test_ensure_greater_than_fails_on_invalid_input() -> None:
    """
    :func:`ensure_greater than` raises ``ValueError`` when the given ``value``
    is not greater than the given ``base_value``.
    """
    inputs: Iterable[tuple[Comparable, Comparable]] = (
        (0, 1),
        (2, 2),
        (-1, 0),
        (-1.0, -0.0),
        (0, 0.999999),
        (-30, -19),
        (-24, -24),
    )
    # With default message
    default_msg: str = "'value' must be greater than 'base_value'."
    for value, base_value in inputs:
        with pytest.raises(ValueError, match="be greater than") as exp_info:
            ensure_greater_than(value, base_value)

        assert exp_info.value.args[0] == default_msg

    # Test with a custom message
    for value, base_value in inputs:
        message: str = f"{value} must be greater than {base_value}"
        with pytest.raises(ValueError, match="be greater than") as exp_info:
            ensure_greater_than(value, base_value, message=message)

        assert exp_info.value.args[0] == message


def test_ensure_instance_of_return_value_on_valid_input() -> None:
    """
    :func:`ensure_instance_of` should return the input value if the given
    input value is an instance of the given type.
    """
    value: Config = Config.of_proxy()

    assert ensure_instance_of(value, Config) is value
    assert ensure_instance_of(value, ConfigProxy) is value
    assert ensure_instance_of(sghi.app.conf, Config) is sghi.app.conf
    assert ensure_instance_of(5, int) == 5


def test_ensure_instance_of_fails_on_invalid_value() -> None:
    """
    :func:`ensure_instance_of` should raise :exc:`TypeError` when given an
    input value of a different type than the specified type.
    """
    with pytest.raises(TypeError, match="not an instance of") as exc_info1:
        ensure_instance_of(sghi.app.conf, dict)

    assert exc_info1.value.args[0] == (
        f"'value' is not an instance of '{type_fqn(dict)}'."
    )

    with pytest.raises(TypeError, match="Invalid value!!") as exc_info2:
        ensure_instance_of(
            value=Config.of_awaiting_setup(),
            klass=ConfigProxy,
            message="Invalid value!!",
        )

    assert exc_info2.value.args[0] == "Invalid value!!"


def test_ensure_less_or_equal_return_value_on_valid_input() -> None:
    """
    :func:`ensure_less_ensure_less_or_equal` should return the input value if
    the given ``value`` is less than or equal to the given ``base_value``.
    """
    assert ensure_less_or_equal(0, 1) == 0
    assert ensure_less_or_equal(2, 2) == 2
    assert ensure_less_or_equal(-1, 0) == -1
    assert ensure_less_or_equal(-0, 0) == 0
    assert ensure_less_or_equal(-1, -1) == -1
    assert ensure_less_or_equal(-1.0, -0.0) == -1.0
    assert ensure_less_or_equal(0, 0.999999) == 0
    assert ensure_less_or_equal(-30, -19) == -30


def test_ensure_less_or_equal_fails_on_invalid_input() -> None:
    """
    :func:`ensure_less_ensure_less_or_equal` raises ``ValueError`` when the
    given ``value`` is not less than or equal to the given ``base_value``.
    """
    inputs: Iterable[tuple[Comparable, Comparable]] = (
        (1, 0),
        (0, -1),
        (-0.0, -1.0),
        (0.999999, 0),
        (-19, -30),
    )
    # With default message
    default_msg: str = "'value' must be less than or equal to 'base_value'."
    for value, base_value in inputs:
        with pytest.raises(ValueError, match="be less than") as exp_info:
            ensure_less_or_equal(value, base_value)

        assert exp_info.value.args[0] == default_msg

    # Test with a custom message
    for value, base_value in inputs:
        message: str = f"{value} must be less than or equal to {base_value}"
        with pytest.raises(ValueError, match="be less than") as exp_info:
            ensure_less_or_equal(value, base_value, message=message)

        assert exp_info.value.args[0] == message


def test_ensure_less_than_return_value_on_valid_input() -> None:
    """
    :func:`ensure_less_than` should return the input value if the given
    ``value`` is less than the given ``base_value``.
    """
    assert ensure_less_than(0, 1) == 0
    assert ensure_less_than(-1, 0) == -1
    assert ensure_less_than(-1.0, -0.0) == -1.0
    assert ensure_less_than(0, 0.999999) == 0
    assert ensure_less_than(-30, -19) == -30


def test_ensure_less_than_fails_on_invalid_input() -> None:
    """
    :func:`ensure_less_than` raises ``ValueError`` when the given ``value`` is
    not less than the given ``base_value``.
    """
    inputs: Iterable[tuple[Comparable, Comparable]] = (
        (1, 0),
        (2, 2),
        (0, -1),
        (-0.0, -1.0),
        (0.999999, 0),
        (-19, -30),
        (-24, -24),
    )
    # With default message
    default_msg: str = "'value' must be less than 'base_value'."
    for value, base_value in inputs:
        with pytest.raises(ValueError, match="be less than") as exp_info:
            ensure_less_than(value, base_value)

        assert exp_info.value.args[0] == default_msg

    # Test with a custom message
    for value, base_value in inputs:
        message: str = f"{value} must be less than {base_value}"
        with pytest.raises(ValueError, match="be less than") as exp_info:
            ensure_less_than(value, base_value, message=message)

        assert exp_info.value.args[0] == message


def test_ensure_not_none_returns_input_value_if_valid() -> None:
    """
    :func:`ensure_not_none`` should return the input value if the value is not
    ``None``.
    """
    value1: str = "A value"
    value2: Sequence[int] = [1, 2, 3, 4, 5]
    value3: int = 0
    value4: bool = False

    assert ensure_not_none(value1) == value1
    assert ensure_not_none(value2) == value2
    assert ensure_not_none(value3) == value3
    assert ensure_not_none(value4) == value4


def test_ensure_not_none_fails_on_invalid_input() -> None:
    """
    :func:`ensure_not_none` should raise a ``ValueError`` when given a ``None``
    input value.
    """
    with pytest.raises(ValueError, match="cannot be None") as exp_info1:
        ensure_not_none(None)
    with pytest.raises(ValueError, match="Invalid") as exp_info2:
        ensure_not_none(None, message="Invalid.")

    assert exp_info1.value.args[0] == '"value" cannot be None.'
    assert exp_info2.value.args[0] == "Invalid."


def test_ensure_not_none_nor_empty_returns_input_value_if_valid() -> None:
    """
    :func:`ensure_not_none_nor_empty` should return the input value if the
    input is not ``None`` or empty.
    """
    value1: str = "A value"
    value2: Sequence[int] = [1, 2, 3, 4, 5]
    value3: Mapping[str, int] = {"one": 1, "two": 2, "three": 3}

    assert ensure_not_none_nor_empty(value1) == value1
    assert ensure_not_none_nor_empty(value2) == value2
    assert ensure_not_none_nor_empty(value3) == value3


def test_ensure_not_none_nor_empty_fails_on_invalid_input() -> None:
    """
    :func:`ensure_not_none_nor_empty`` should raise a ``ValueError`` when given
    a ``None`` or empty ``Sized`` value as input.
    """
    with pytest.raises(ValueError, match="cannot be None or emp") as exp_info1:
        ensure_not_none_nor_empty(None)  # type: ignore
    with pytest.raises(ValueError, match="Invalid") as exp_info2:
        ensure_not_none_nor_empty(None, message="Invalid.")  # type: ignore
    with pytest.raises(ValueError, match="cannot be None or emp") as exp_info3:
        ensure_not_none_nor_empty("")
    with pytest.raises(ValueError, match="Invalid") as exp_info4:
        ensure_not_none_nor_empty([], message="Invalid.")

    assert exp_info1.value.args[0] == '"value" cannot be None or empty.'
    assert exp_info2.value.args[0] == "Invalid."
    assert exp_info3.value.args[0] == '"value" cannot be None or empty.'
    assert exp_info4.value.args[0] == "Invalid."


def test_ensure_optional_instance_of_return_value_on_valid_input() -> None:
    """
    :func:`ensure_optional_instance_of` should return the input value if the
    given input value is ``None`` or an instance of the given type.
    """
    value: Config = Config.of_proxy()

    assert ensure_optional_instance_of(None, str) is None
    assert ensure_optional_instance_of(value, Config) is value
    assert ensure_optional_instance_of(value, ConfigProxy) is value
    assert ensure_optional_instance_of(sghi.app.conf, Config) is sghi.app.conf
    assert ensure_optional_instance_of(5, int) == 5


def test_ensure_optional_instance_of_fails_on_invalid_value() -> None:
    """
    :func:`ensure_optional_instance_of` should raise :exc:`TypeError` when
    given an input value of a different type than the specified type.
    """
    with pytest.raises(TypeError, match="not an instance of") as exc_info1:
        ensure_optional_instance_of(sghi.app.conf, dict)

    assert exc_info1.value.args[0] == (
        f"'value' is not an instance of '{type_fqn(dict)}' or None."
    )

    with pytest.raises(TypeError, match="Invalid value!!") as exc_info2:
        ensure_optional_instance_of(
            value=Config.of_awaiting_setup(),
            klass=ConfigProxy,
            message="Invalid value!!",
        )

    assert exc_info2.value.args[0] == "Invalid value!!"


def test_ensure_predicate_with_successfully_predicate_evaluation() -> None:
    """
    :func:`ensure_predicate` should return silently without raising any
    exception whenever the given predicate test evaluates to ``True``.
    """
    try:
        ensure_predicate(6 >= 6)
        ensure_predicate(9 > 4)
        ensure_predicate(True)
        ensure_predicate(len("A string") > 0)
    except BaseException as exc:  # noqa: BLE001
        pytest.fail(reason=f"'ensure_predicate()' raised {exc!s} unexpectedly")


def test_ensure_predicate_with_failing_predicate_evaluation() -> None:
    """
    :func:`ensure_predicate` should raise an exception whenever the given
    predicate test evaluates to ``False``.
    """
    tests1: Iterable[bool] = (
        6 > 6,
        9 < 5,
        False,
        len("A string") == 1,
    )
    default_msg: str = "Invalid value. Predicate evaluation failed."
    for test in tests1:
        with pytest.raises(ValueError, match="evaluation failed.") as exc_info:
            ensure_predicate(test)
        assert exc_info.value.args[0] == default_msg

    tests2: Iterable[bool] = (
        isinstance(6, str),
        isinstance(6, float),
    )
    for test in tests2:
        with pytest.raises(TypeError, match="Invalid input type.") as exc_info:
            ensure_predicate(
                test,
                message="Invalid input type.",
                exc_factory=TypeError,
            )
        assert exc_info.value.args[0] == "Invalid input type."
