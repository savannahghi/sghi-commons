"""``Retry`` interface definition and a few of its implementations.

This module defines the :class:`Retry` interface, which allows applications to
specify policies for retrying operations that may fail due to transient errors.
"""

from __future__ import annotations

import logging
import random
import time
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import cache, wraps
from logging import Logger
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    ParamSpec,
    TypeVar,
    final,
)

from typing_extensions import override

from sghi.exceptions import SGHIError, SGHITransientError
from sghi.utils import (
    ensure_greater_or_equal,
    ensure_greater_than,
    ensure_predicate,
    type_fqn,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

# =============================================================================
# TYPES
# =============================================================================

_P = ParamSpec("_P")
_RT = TypeVar("_RT")

_RetryPredicate = Callable[[BaseException], bool]


# =============================================================================
# CONSTANTS
# =============================================================================


_DEFAULT_INITIAL_DELAY: Final[float] = 2.0  # In seconds

_DEFAULT_MAXIMUM_DELAY: Final[float] = 60.0  # In seconds

_DEFAULT_MULTIPLICATIVE_FACTOR: Final[float] = 2.0

_DEFAULT_TIMEOUT: Final[float] = 60.0 * 5  # In seconds


# =============================================================================
# EXCEPTIONS
# =============================================================================


class RetryError(SGHIError):
    """An exception used to indicate that a retry failed.

    This is raised once a :class:`retry policy<Retry>` exhausts all it's
    available retries.
    """

    def __init__(
        self,
        cause: BaseException,
        message: str | None = None,
    ) -> None:
        """Initialize a ``RetryError`` from the given cause and message.

        :param cause: The last exception raised when retrying the failed
            operation.
        :param message: An optional error message detailing the failure.
            Defaults to ``None`` when not provided.
        """
        super().__init__(message=message)
        self._cause: BaseException = cause

    @property
    def cause(self) -> BaseException:
        """The last exception raised when retrying the failed operation."""
        return self._cause


# =============================================================================
# HELPERS
# =============================================================================


def if_exception_type_factory(
    *exp_types: type[BaseException],
) -> _RetryPredicate:
    """Create a retry predicate for the given exception types.

    :param exp_types: The exception types to check for.

    :return: A callable that takes an exception and returns ``True`` if the
        provided exception is of the given types.
    """
    _exp: BaseException
    return lambda _exp: isinstance(_exp, exp_types)


if_transient_exception = if_exception_type_factory(SGHITransientError)
"""
Retry predicate that checks if an exception is an
:exc:`~sghi.exceptions.SGHITransientError`.
"""


# =============================================================================
# RETRY INTERFACE
# =============================================================================


class Retry(metaclass=ABCMeta):
    """An object that defines a retry policy.

    A retry policy allows an application to handle transient failures such as
    when trying to connect to a network resource or another service. This is
    achieved by transparently repeating the failed operation until it succeeds
    or until some criteria are met.

    This interface defines one abstract method, :meth:`retry`, that wraps a
    callable object that requires retrying. Subclasses should override this
    method to provide a retry policy implementation that best suits the
    application's needs.

    Instances of this interface can be used as callables in which case the
    actual call is delegated to the ``retry`` method. This enables the
    instances to be used as decorators on other callable objects (that
    require retrying).

    .. caution::

        Only apply to idempotent operations to avoid unintended side effects.
    """

    __slots__ = ()

    def __call__(self, f: Callable[_P, _RT]) -> Callable[_P, _RT]:
        """Wrap the given callable and retry it if it fails or as necessary.

        This method delegates the actual call to the :meth:`retry` method. It
        also allows instances of this class to be used as decorators on other
        callable objects (that require retrying).

        :param f: A callable object that requires retrying.

        :return: A new callable that wraps the original callable to provide
            a retry mechanism.

        :raise RetryError: If the retry fails.
        """
        return self.retry(f)

    @abstractmethod
    def retry(self, f: Callable[_P, _RT]) -> Callable[_P, _RT]:
        """Wrap the given callable and retry it if it fails or as necessary.

        This method implements the actual retry policy. It accepts a callable
        object that requires retrying and wraps it around a mechanism that
        retries the callable in case of failure. The newly wrapped callable is
        then returned to the caller, allowing it to be invoked as usual.

        A :exc:`~sghi.retry.RetryError` will be raised if the retry fails.

        .. caution::

            Only apply to idempotent operations to avoid unintended side
            effects.

        :param f: A callable object that requires retrying.

        :return: A new callable that wraps the original callable to provide
            a retry mechanism.

        :raise RetryError: If the retry fails.
        """
        ...

    @staticmethod
    @cache
    def of_exponential_backoff(
        predicate: _RetryPredicate | None = None,
        initial_delay: float = _DEFAULT_INITIAL_DELAY,
        maximum_delay: float = _DEFAULT_MAXIMUM_DELAY,
        timeout: float | None = _DEFAULT_TIMEOUT,
        multiplicative_factor: float = _DEFAULT_MULTIPLICATIVE_FACTOR,
    ) -> Retry:
        """Return a :class:`Retry` that uses the exponential backoff algorithm.

        The returned instance/policy will exponentially retry an operation
        until it succeeds or until a timeout is exceeded. If a timeout is not
        provided, the retry will continue indefinitely (till the heat death of
        the universe) or until the operation succeeds.

        A predicate function to determine when it is appropriate to retry a
        failed operation can be provided. By default, only
        :exc:`~sghi.exceptions.SGHITransientError` exceptions are retried.

        .. note::

            The instances returned by this method are NOT guaranteed to be
            distinct on each invocation.

        :param predicate: A callable that accepts an exception as its sole
            parameter and, should return ``True`` if the exception is
            retryable or ``False`` otherwise.
        :param initial_delay: The minimum duration to delay in seconds, this
            MUST be greater than zero.
        :param maximum_delay: The maximum duration to delay in seconds. This
            MUST be greater than or equal to ``initial_delay``.
        :param timeout: The maximum duration to keep retrying in seconds. The
            last delay will be shortened as necessary to ensure that the retry
            runs no later than ``timeout`` seconds. If ``None`` is given, the
            retry will run indefinitely or until the operation succeeds.
        :param multiplicative_factor: The multiplier applied to the delay on
            each retry. This MUST be greater than zero.

        :return: A ``Retry`` instance that uses the exponential backoff
            algorithm.

        :raise ValueError: If either ``initial_delay`` or
            ``multiplicative_factor`` are NOT greater than zero, or if
            ``maximum_delay`` is NOT greater or equal to ``initial_delay``.
            This error will also be raised if ``predicate`` is not a callable.
        """
        return _ExponentialBackOffRetry(
            predicate=predicate or if_transient_exception,
            initial_delay=initial_delay,
            maximum_delay=maximum_delay,
            timeout=timeout,
            multiplicative_factor=multiplicative_factor,
        )

    @staticmethod
    @cache
    def of_noop() -> Retry:
        """Return a :class:`Retry` instance that does nothing.

        Instances returned by this method return the
        :meth:`wrapped callable<sghi.retry.Retry.retry>` as is. This can be
        useful as a placeholder where a ``Retry`` instance is required or to
        disable the retry behavior.

        .. note::

            The instances returned by this method are NOT guaranteed to be
            distinct on each invocation.

        :return: A ``Retry`` instance that does nothing.
        """
        return _NoOpRetry()


# =============================================================================
# RETRY IMPLEMENTATIONS
# =============================================================================


@final
class _ExponentialBackOffRetry(Retry):
    __slots__ = (
        "_predicate",
        "_initial_delay",
        "_maximum_delay",
        "_timeout",
        "_multiplicative_factor",
        "_logger",
    )

    def __init__(
        self,
        predicate: _RetryPredicate,
        initial_delay: float = _DEFAULT_INITIAL_DELAY,
        maximum_delay: float = _DEFAULT_MAXIMUM_DELAY,
        timeout: float | None = _DEFAULT_TIMEOUT,
        multiplicative_factor: float = _DEFAULT_MULTIPLICATIVE_FACTOR,
    ) -> None:
        ensure_predicate(
            callable(predicate),
            message="'predicate' MUST be a callable.",
        )
        self._predicate: _RetryPredicate = predicate
        self._initial_delay: float = ensure_greater_than(
            value=initial_delay,
            base_value=0.0,
            message="'initial_delay' MUST be greater than 0.",
        )
        self._maximum_delay: float = ensure_greater_or_equal(
            value=maximum_delay,
            base_value=initial_delay,
            message=(
                f"The 'maximum_delay' ({maximum_delay:.2f}) MUST be greater "
                f"than or equal to the 'initial_delay' ({initial_delay:.2f})."
            ),
        )
        self._timeout: float | None = timeout
        self._multiplicative_factor: float = ensure_greater_than(
            value=multiplicative_factor,
            base_value=0.0,
            message="'multiplicative_factor' MUST be greater than 0.",
        )
        self._logger: Logger = logging.getLogger(type_fqn(self.__class__))

    @override
    def retry(self, f: Callable[_P, _RT]) -> Callable[_P, _RT]:
        @wraps(f)
        def do_retry(*args: _P.args, **kwargs: _P.kwargs) -> _RT:
            deadline_time: datetime | None = self._calculate_deadline_time()
            last_exp: BaseException

            for delay in self._exponential_delay_generator():
                try:
                    return f(*args, **kwargs)
                except Exception as exp:  # noqa: BLE001
                    if not self._predicate(exp):
                        raise
                    last_exp = exp

                delay = self._deliberate_next_retry(
                    next_delay_duration=delay,
                    deadline_time=deadline_time,
                    last_exp=last_exp,
                    f=f,
                )
                self._logger.warning(
                    'Retrying due to "%s", waiting for %.2f seconds before '
                    "the next attempt ...",
                    last_exp,
                    delay,
                )
                time.sleep(delay)

            # This should never be reached. This method should either exit by
            # returning the wrapped callable's result or by raising an
            # exception.
            err_msg: str = "The program entered an invalid state. Exiting."  # pragma: no cover # noqa: E501
            raise AssertionError(err_msg)

        return do_retry

    def _calculate_deadline_time(self) -> datetime | None:
        """Determine and return the time when the last retry should be made.

        This method is should only be called once per :class:`Retry <retry>`
        instance. Return the calculated timeout time or ``None`` to indicate
        that the callable should be retried indefinitely until a successful
        call is made.

        :return: The calculated timeout time or ``None``.
        """
        timeout: float | None = self._timeout
        now = datetime.now
        return now() + timedelta(seconds=timeout) if timeout else None

    def _deliberate_next_retry(
        self,
        next_delay_duration: float,
        deadline_time: datetime | None,
        last_exp: BaseException,
        f: Callable[..., Any],
    ) -> float:
        """Make a decision on whether to perform the next retry or fail.

        In case of failure, mark the retry as failed by raising a
        :exc:`RetryError`. A retry is considered as failed if the set
        timeout has already been exceeded.

        Return the duration to delay before the next retry.

        :param next_delay_duration: The next delay duration returned by the
            exponential delay generator.
        :param deadline_time: The time when the last retry should be made. When
            not ``None``, the returned delay duration will be adjusted as
            necessary not to exceed this value.
        :param last_exp: The last exception that was raised.
        :param f: The callable been retried. This is only needed for logging
            purposes.

        :return: The next delay duration before making the next retry. This
            will be adjusted not to exceed the given timeout time.

        :raise RetryError: If the timeout has already been exceeded.
        """
        if deadline_time is None:  # pragma: no cover
            return next_delay_duration
        now: datetime = datetime.now()
        if now > deadline_time:
            raise RetryError(
                message=(
                    f"Timeout of {self._timeout:.2f}s exceeded while "
                    f"retrying '{type_fqn(f)}'."
                ),
                cause=last_exp,
            ) from last_exp

        remaining_time = (deadline_time - now).total_seconds()
        return min(remaining_time, next_delay_duration)

    def _exponential_delay_generator(self) -> Iterable[float]:
        """Return an exponential delay generator.

        Return a generator that yields successive delay intervals based on the
        exponential back-off algorithm.

        :return: An exponential delay generator.
        """
        delay: float = self._initial_delay
        while True:
            yield min(random.uniform(0.0, delay * 2.0), self._maximum_delay)  # noqa: S311
            delay *= self._multiplicative_factor


@final
class _NoOpRetry(Retry):
    __slots__ = ()

    @override
    def retry(self, f: Callable[_P, _RT]) -> Callable[_P, _RT]:
        return f


exponential_backoff_retry = Retry.of_exponential_backoff

noop_retry = Retry.of_noop
