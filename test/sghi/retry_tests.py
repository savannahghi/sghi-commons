from __future__ import annotations

from typing import TypeVar
from unittest import TestCase

import pytest

from sghi.exceptions import SGHITransientError
from sghi.retry import (
    Retry,
    RetryError,
    if_exception_type_factory,
    if_transient_exception,
)

# =============================================================================
# TYPES
# =============================================================================


_T = TypeVar("_T")


# =============================================================================
# TESTS HELPERS
# =============================================================================


def as_is(val: _T) -> _T:
    """Function that takes a value and returns the value unchanged."""
    return val


# =============================================================================
# TESTS
# =============================================================================


def test_if_exception_type_factory_returns_expected_value() -> None:
    """:func:`~sghi.retry.if_exception_type_factory` should return retry
    predicates for the provided exception(s).
    """

    predicate = if_exception_type_factory(RuntimeError, ValueError)

    assert predicate(RuntimeError())
    assert predicate(ValueError())
    assert not predicate(ZeroDivisionError())
    assert not predicate(SGHITransientError())


def test_if_transient_exception_return_value() -> None:
    """:func:`~sghi.retry.if_transient_exception` should return ``True`` for
    all :exc:`~sghi.exc.SGHITransientError` exceptions.
    """

    class DBConnectionError(SGHITransientError):
        """A transient connection error to a DB."""

    assert if_transient_exception(SGHITransientError())
    assert if_transient_exception(DBConnectionError())
    assert not if_transient_exception(RetryError(DBConnectionError()))


class TestRetry(TestCase):
    """Tests of the :class:`~sghi.etl.retry.Retry` interface.

    Tests for the default method implementations on the `Retry` interface.
    """

    def test_invoking_retry_as_a_callable_returns_expected_value(self) -> None:
        """
        :class:`~sghi.retry.Retry` instances should return the expected value
        when invoked as callables.

        That is, invoking a ``Retry`` instance as a callable should delegate
        the actual call to the :meth:`~sghi.retry.Retry.retry` method of the
        same instance.
        """

        instance: Retry = Retry.of_noop()

        assert instance(as_is)(10) == instance.retry(as_is)(10) == 10

    def test_using_retry_as_decorator_has_intended_side_effects(self) -> None:
        """
        :class:`~sghi.retry.Retry` instances should have the same side effects
        as invoking :meth:`~sghi.retry.Retry.retry`, even when used as
        decorators.
        """
        instance: Retry = Retry.of_exponential_backoff(
            predicate=if_transient_exception,
            initial_delay=1,
            maximum_delay=2,
            timeout=10,
        )

        fail_count: int = 0

        @instance
        def fail_thrice(val: int) -> int:
            nonlocal fail_count
            while fail_count < 3:
                fail_count += 1
                _err_msg: str = "Simulated error."
                raise SGHITransientError(_err_msg)

            return val

        assert fail_thrice(10) == 10
        assert fail_count == 3

    def test_of_exponential_backoff_return_value(self) -> None:
        """:meth:`~sghi.retry.Retry.of_exponential_backoff` should return a
        ``Retry`` instance.
        """

        assert isinstance(Retry.of_exponential_backoff(), Retry)

    def test_of_noop_return_value(self) -> None:
        """:meth:`~sghi.retry.Retry.of_noop` should return a ``Retry``
        instance.
        """

        assert isinstance(Retry.of_noop(), Retry)


class TestsRetryOfExponentialBackoff(TestCase):
    """Tests for the ``Retry.of_exponential_backoff`` Retry implementation.

    This testcase defines tests for the :class:`~sghi.retry.Retry`
    implementation returned by the
    :meth:`~sghi.retry.Retry.of_exponential_backoff` factory method.
    """

    def test_initialization_fails_with_invalid_initial_delay(self) -> None:
        """:meth:`~sghi.retry.Retry.of_exponential_backoff` should fail
        when given an invalid 'initial_delay'.
        """

        for i in (-1, 0, -2, -0):
            with pytest.raises(ValueError, match="greater than 0"):
                Retry.of_exponential_backoff(initial_delay=i)

        with pytest.raises(ValueError, match="greater than 0") as exp_info:
            Retry.of_exponential_backoff(initial_delay=-10)

        assert (
            exp_info.value.args[0] == "'initial_delay' MUST be greater than 0."
        )

    def test_initialization_fails_with_invalid_maximum_delay(self) -> None:
        """:meth:`~sghi.retry.Retry.of_exponential_backoff` should fail
        when given an invalid 'maximum_delay'.
        """

        for m in (-1, 0, -2, -0):
            with pytest.raises(ValueError, match="greater than or equal"):
                Retry.of_exponential_backoff(initial_delay=1, maximum_delay=m)

        with pytest.raises(ValueError, match="greater than or eq") as exp_info:
            Retry.of_exponential_backoff(initial_delay=2, maximum_delay=1)

        assert (
            exp_info.value.args[0]
            == "The 'maximum_delay' (1.00) MUST be greater than or equal to "
            "the 'initial_delay' (2.00)."
        )

    def test_initialization_fails_with_invalid_multiplicative_factor(
        self,
    ) -> None:
        """:meth:`~sghi.retry.Retry.of_exponential_backoff` should fail
        when given an invalid 'multiplicative_factor'.
        """

        for i in (-1, 0, -2, -0):
            with pytest.raises(ValueError, match="greater than 0"):
                Retry.of_exponential_backoff(multiplicative_factor=i)

        with pytest.raises(ValueError, match="greater than 0") as exp_info:
            Retry.of_exponential_backoff(multiplicative_factor=-10)

        assert (
            exp_info.value.args[0]
            == "'multiplicative_factor' MUST be greater than 0."
        )

    def test_initialization_fails_with_invalid_predicate(self) -> None:
        """:meth:`~sghi.retry.Retry.of_exponential_backoff` should fail
        when given an invalid 'predicate'.
        """

        with pytest.raises(ValueError, match="be a callable") as exp_info:
            Retry.of_exponential_backoff(predicate="Not a callable")

        assert exp_info.value.args[0] == "'predicate' MUST be a callable."

    def test_retry_fails_fast_if_predicate_fails(self) -> None:
        """:meth:`~sghi.retry.Retry.of_exponential_backoff` instances should
        fail fast if the given retry predicate fails for the raised exception.
        """
        if_runtime_exception = if_exception_type_factory(RuntimeError)

        instance: Retry = Retry.of_exponential_backoff(
            predicate=if_runtime_exception,
            initial_delay=1,
            maximum_delay=2,
            timeout=10,
        )

        fail_count: int = 0

        @instance
        def fail_thrice(val: int) -> int:
            nonlocal fail_count
            while fail_count < 3:
                fail_count += 1
                _err_msg: str = "Simulated error."
                raise SGHITransientError(_err_msg)

            return val

        with pytest.raises(SGHITransientError, match="Simulated error."):
            fail_thrice(10)

        assert fail_count == 1

    def test_retry_succeeds_while_timeout_not_exceeded(self) -> None:
        """:meth:`~sghi.retry.Retry.of_exponential_backoff` instances should
        retry successfully while the timeout has not yet been exceeded.
        """
        instance: Retry = Retry.of_exponential_backoff(
            predicate=if_transient_exception,
            initial_delay=1,
            maximum_delay=2,
            timeout=10,
        )

        fail_count: int = 0

        @instance
        def fail_thrice(val: int) -> int:
            nonlocal fail_count
            while fail_count < 3:
                fail_count += 1
                _err_msg: str = "Simulated error."
                raise SGHITransientError(_err_msg)

            return val

        try:
            assert fail_thrice(10) == 10
        except SGHITransientError:
            pytest.fail("'fail_thrice' should have succeeded.")

        assert fail_count == 3

    def test_retry_side_effects_with_timeout_exceeded(self) -> None:
        """:meth:`~sghi.retry.Retry.of_exponential_backoff` instances should
        raise :exc:`RetryError` once the retry timeout is exceeded without a
        successful call.
        """
        instance: Retry = Retry.of_exponential_backoff(
            predicate=if_transient_exception,
            initial_delay=2,
            maximum_delay=2,
            timeout=1,
        )

        @instance
        def fail_always() -> None:
            _err_msg: str = "Simulated error."
            raise SGHITransientError(_err_msg)

        with pytest.raises(RetryError) as exp_info:
            fail_always()

        assert exp_info.value.cause.__class__ == SGHITransientError
        assert exp_info.value.message is not None
        assert exp_info.value.message.startswith("Timeout of 1.00s exceeded")
