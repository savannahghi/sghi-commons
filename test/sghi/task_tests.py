import operator
import time
from collections.abc import Sequence
from concurrent.futures import wait
from functools import partial
from typing import TYPE_CHECKING
from unittest import TestCase

import pytest

from sghi.task import (
    ConcurrentExecutor,
    ConcurrentExecutorDisposedError,
    Task,
    chain,
    consume,
    pipe,
    task,
)
from sghi.utils import ensure_greater_than, future_succeeded

if TYPE_CHECKING:
    from collections.abc import Callable


def test_task_decorator_fails_on_non_callable_input_value() -> None:
    """
    :func:`task` should raise a :exc:`ValueError` when given a non-callable`
    value.
    """

    with pytest.raises(ValueError, match="callable object") as exc_info:
        task("Not a function")  # type: ignore

    assert exc_info.value.args[0] == "A callable object is required."


def test_task_decorator_fails_on_a_none_input_value() -> None:
    """
    :func:`task` should raise a :exc:`ValueError` when given a ``None`` value.
    """

    with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
        task(None)  # type: ignore

    assert exc_info.value.args[0] == "The given callable MUST not be None."


def test_task_decorator_returns_correct_value() -> None:
    """
    :func:`task` should return a ``Task`` instance with the same semantics as
    the wrapped callable.
    """

    add_100: Callable[[int], int] = partial(operator.add, 100)
    add_100_task: Task[int, int] = task(add_100)

    @task
    def int_to_str(value: int) -> str:
        return str(value)

    assert add_100(10) == add_100_task(10) == 110
    assert add_100(-10) == add_100_task(-10) == 90
    assert int_to_str(10) == str(10) == "10"
    assert int_to_str.execute(3) == str(3) == "3"


def test_task_decorator_returns_expected_value() -> None:
    """:func:`task` should return a ``Task`` instance."""

    add_100: Callable[[int], int] = partial(operator.add, 100)
    add_100_task: Task[int, int] = task(add_100)

    @task
    def int_to_str(value: int) -> str:
        return str(value)

    assert isinstance(add_100_task, Task)
    assert isinstance(int_to_str, Task)


class TestConsume(TestCase):
    """Tests for the :class:`consume` ``Task``."""

    def test_and_then_method_returns_expected_value(self) -> None:
        """:meth:`consume.and_then` method should return a new instance of
        :class:`consume` that composes both the action of the current
        ``consume`` instance and the new action.
        """
        collection1: list[int] = []
        collection2: set[int] = set()

        collector: consume[int]
        collector = consume(collection1.append).and_then(collection2.add)

        assert isinstance(collector, consume)

        collector.execute(10)
        assert len(collection1) == len(collection2) == 1

        collector.execute(20)
        assert len(collection1) == len(collection2) == 2

        collector.execute(30)
        assert len(collection1) == len(collection2) == 3

    def test_instantiation_with_a_none_input_fails(self) -> None:
        """
        :class:`consume` constructor should raise ``ValueError`` when given a
        ``None`` input.
        """
        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            consume(accept=None)  # type: ignore

        assert exc_info.value.args[0] == "'accept' MUST not be None."

    def test_execute_performs_the_expected_side_effects(self) -> None:
        """
        :meth:`consume.execute` method should apply it's input to the wrapped
        action only, i.e., it should perform it's intended side effects only.
        """
        results: list[int] = []
        collector: consume[int] = consume(accept=results.append)

        assert collector.execute(10) == 10
        assert len(results) == 1
        assert results[0] == 10

        assert collector.execute(20) == 20
        assert len(results) == 2
        assert results[0] == 10
        assert results[1] == 20

        value: int = 30
        assert collector.execute(value) == value
        assert len(results) == 3
        assert results[0] == 10
        assert results[1] == 20
        assert results[2] == value
        assert value == 30  # value should not have changed

    def test_different_and_then_method_invocation_styles_return_same_value(
        self,
    ) -> None:
        """
        :meth:`consume.execute` should return the same value regardless of how
        it was invoked.
        """
        collection1: list[int] = []
        collection2: set[int] = set()
        collection3: list[int] = []
        collection4: set[int] = set()

        # Style 1, explicit invocation
        collector1: consume[int]
        collector1 = consume(collection1.append).and_then(collection2.add)
        # Style 2, using the plus operator
        collector2: consume[int]
        collector2 = consume(collection3.append) + collection4.add

        assert isinstance(collector1, consume)
        assert isinstance(collector2, consume)

        collector1(10)
        collector2(10)
        assert len(collection1) == len(collection2) == 1
        assert len(collection3) == len(collection4) == 1

        collector1(20)
        collector1(30)
        collector2(20)
        collector2(30)
        assert len(collection1) == len(collection2) == 3
        assert len(collection3) == len(collection4) == 3

    def test_different_execute_invocation_styles_return_same_value(
        self,
    ) -> None:
        """
        :meth:`consume.execute` should return the same value regardless of how
        it was invoked.
        """
        results1: list[int] = []
        collector1: consume[int] = consume(accept=results1.append)
        results2: list[int] = []
        collector2: consume[int] = consume(accept=results2.append)

        # Style 1, explicit invocation
        collector1.execute(10)
        # Style 2, invoke as callable
        collector2(10)

        assert len(results1) == len(results2) == 1
        assert results1[0] == results2[0] == 10

        # Style 1, explicit invocation
        collector1.execute(20)
        # Style 2, invoke as callable
        collector2(20)

        assert len(results1) == len(results2) == 2
        assert results1[0] == results2[0] == 10
        assert results1[1] == results2[1] == 20


class TestChain(TestCase):
    """Tests for the :class:`chain` ``Task``."""

    def setUp(self) -> None:
        super().setUp()
        self._add_30 = partial(operator.add, 30)
        self._multiply_by_2 = partial(operator.mul, 2)
        self._chain_of_10: chain = chain(10)

    def test_execute_fails_on_none_input(self) -> None:
        """
        :meth:`chain.execute` method should raise a :exc:`ValueError` when
        invoked with a ``None`` argument.
        """
        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            self._chain_of_10(None)  # type: ignore

        assert exc_info.value.args[0] == "'an_input' MUST not be None."

    def test_execute_return_value(self) -> None:
        """
        :meth:`chain.execute` method should return a new :class:`chain`
        instance with the new computed value.
        """
        instance: chain[int]
        instance = self._chain_of_10.execute(self._multiply_by_2).execute(
            self._add_30
        )

        assert isinstance(self._chain_of_10.execute(self._add_30), chain)
        assert self._chain_of_10.execute(self._multiply_by_2).value == 20
        assert self._chain_of_10.execute(self._add_30).value == 40
        assert instance.value == 50

    def test_different_execute_invocation_styles_return_same_value(
        self,
    ) -> None:
        """
        :meth:`chain.execute` should return the same value regardless of how
        it was invoked.
        """
        instance1: chain[int]
        instance2: chain[int]
        instance3: chain[int]

        # Style 1, explicit invocation
        instance1 = self._chain_of_10.execute(self._multiply_by_2).execute(
            self._add_30
        )
        # Style 2, invoke as callable
        instance2 = self._chain_of_10(self._multiply_by_2)(self._add_30)
        # Style 3, using the plus operator
        instance3 = self._chain_of_10 + self._multiply_by_2 + self._add_30

        assert instance1.value == instance2.value == instance3.value == 50

    def test_value_property_return_value(self) -> None:
        """
        :attr:`chain.value` should return the wrapped value of the current
        chain instance.
        """
        assert self._chain_of_10.value == 10
        assert self._chain_of_10(self._multiply_by_2).value == 20
        assert self._chain_of_10(self._add_30).value == 40


class TestConcurrentExecutor(TestCase):
    """Tests for the :class:`ConcurrentExecutor` ``Task``."""

    def setUp(self) -> None:
        super().setUp()
        self._longer_io_tasks: Sequence[Task[float, float]] = tuple(
            Task.of_callable(self._do_longer_io_bound_task) for _ in range(3)
        )
        self._short_io_tasks: Sequence[Task[float, float]] = tuple(
            Task.of_callable(self._do_io_bound_task) for _ in range(5)
        )
        self._blocking_executor: ConcurrentExecutor[float, float]
        self._blocking_executor = ConcurrentExecutor(
            *self._longer_io_tasks,
            *self._short_io_tasks,
        )
        self._non_blocking_executor: ConcurrentExecutor[float, float]
        self._non_blocking_executor = ConcurrentExecutor(
            *self._longer_io_tasks,
            *self._short_io_tasks,
            wait_for_completion=False,
        )

    def tearDown(self) -> None:
        super().tearDown()
        self._blocking_executor.dispose()
        self._non_blocking_executor.dispose()

    def test_enter_context_on_a_disposed_executor_fails(self) -> None:
        """
        :meth:`ConcurrentExecutor.__enter__` should raise
        :exc:`ConcurrentExecutorDisposedError` when invoked on a disposed
        instance.
        """
        self._blocking_executor.dispose()
        self._non_blocking_executor.dispose()

        ced = ConcurrentExecutorDisposedError
        err_msg: str = "ConcurrentExecutor disposed."
        with pytest.raises(ced) as exc_info1:  # noqa: SIM117
            with self._blocking_executor:
                ...

        with pytest.raises(ced) as exc_info2:  # noqa: SIM117
            with self._non_blocking_executor:
                ...

        assert exc_info1.value.message == err_msg
        assert exc_info2.value.message == err_msg

    def test_enter_context_on_non_blocking_mode_warns(self) -> None:
        """
        :meth:`ConcurrentExecutor.__enter__` should warn the user. This is
        most likely erroneous API usage.
        """
        with pytest.warns(UserWarning, match="is discouraged"):  # noqa: SIM117
            with self._non_blocking_executor:
                ...

    def test_failing_wrapped_tasks_errors_are_re_raised(self) -> None:
        """
        Errors raised by the :meth:`ConcurrentExecutor.execute` should be
        propagated as is the returned futures.
        """
        tasks = tuple(self._do_failing_io_bound_task for _ in range(3))
        with ConcurrentExecutor(*tasks) as executor:
            futures = tuple(executor(2))
            for exc in map(operator.methodcaller("exception"), futures):
                assert isinstance(exc, ZeroDivisionError)

    def test_execute_invocation_on_a_disposed_executor_fails(self) -> None:
        """
        :meth:`ConcurrentExecutor.execute` should raise a
        :exc:`ConcurrentExecutorDisposedError` when invoked on a disposed
        instance.
        """
        self._blocking_executor.dispose()
        self._non_blocking_executor.dispose()

        err_msg: str = "ConcurrentExecutor disposed."
        with pytest.raises(ConcurrentExecutorDisposedError) as exc_info1:
            self._blocking_executor(10)

        with pytest.raises(ConcurrentExecutorDisposedError) as exc_info2:
            self._non_blocking_executor(30)

        assert exc_info1.value.message == err_msg
        assert exc_info2.value.message == err_msg

    def test_execute_return_value_in_blocking_mode(self) -> None:
        """
        :meth:`ConcurrentExecutor.execute` method should return completed
        futures.
        """
        with self._blocking_executor as executor:
            futures = tuple(executor(3))

            # All futures should be complete by the time execute returns.
            assert all(map(future_succeeded, futures))
            assert all(
                v == 3.0 or v == 9.0
                for v in map(operator.methodcaller("result", 1), futures)
            )
            assert len(futures) == (
                len(self._longer_io_tasks) + len(self._short_io_tasks)
            )
            futures[0].result()

    def test_execute_return_value_in_non_blocking_mode(self) -> None:
        """
        :meth:`ConcurrentExecutor.execute` method should return immediately
        after scheduling tasks to be executed concurrently. This means that
        some/all tasks will not have completed yet once the method returns.
        """
        futures = tuple(self._non_blocking_executor(2))

        # FIXME: Find a better test, this might fail due to a race condition.
        assert any(
            # Not completed. That is, check that some future has not yet
            # completed.
            map(operator.not_, map(operator.methodcaller("done"), futures)),
        )
        wait(futures)
        assert all(
            v == 2.0 or v == 6.0
            for v in map(operator.methodcaller("result", 1), futures)
        )
        assert len(futures) == (
            len(self._longer_io_tasks) + len(self._short_io_tasks)
        )

    def test_dispose_side_effects(self) -> None:
        """
        :meth:`ConcurrentExecutor.dispose` should result in the
        :attr:`ConcurrentExecutor.is_disposed` property returning ``True``.
        """
        assert not self._blocking_executor.is_disposed
        assert not self._non_blocking_executor.is_disposed

        self._blocking_executor.dispose()
        self._non_blocking_executor.dispose()

        assert self._blocking_executor.is_disposed
        assert self._non_blocking_executor.is_disposed

    @staticmethod
    def _do_failing_io_bound_task(task_input: float) -> float:
        tce = TestConcurrentExecutor
        return tce._do_io_bound_task(task_input) / 0

    @staticmethod
    def _do_io_bound_task(task_input: float) -> float:
        ensure_greater_than(task_input, 0, message="expected task_input > 0")
        time.sleep(task_input)
        return task_input

    @staticmethod
    def _do_longer_io_bound_task(task_input: float) -> float:
        tce = TestConcurrentExecutor
        return tce._do_io_bound_task(task_input * 3)


class TestPipe(TestCase):
    """Tests for the :class:`pipe` ``Task``."""

    def setUp(self) -> None:
        super().setUp()
        self._add_100: Callable[[int], int] = partial(operator.add, 100)
        self._multiply_by_10: Callable[[int], int] = partial(operator.mul, 10)
        self._instance: pipe[int, str] = pipe(
            self._add_100,
            self._add_100,
            self._add_100,
            self._add_100,
            Task.of_callable(self._add_100),
            Task.of_callable(self._multiply_by_10),
            str,
        )

    def test_execute_return_value(self) -> None:
        """
        :meth:`pipe.execute` should return the value of applying it's input
        value to all it's tasks sequentially.
        """
        assert self._instance(0) == "5000"
        assert self._instance(500) == "10000"
        assert self._instance(-500) == "0"

    def test_pipe_instantiation_with_empty_tasks_fails(self) -> None:
        """
        Instantiation of :class:`pipe` with no tasks should raise
        ``ValueError``.
        """
        with pytest.raises(ValueError, match="MUST not be None or empty."):
            pipe()

    def test_tasks_property_return_value(self) -> None:
        """
        :attr:`pipe.tasks` should return the ``Sequence`` of tasks that
        comprise the ``pipe``.
        """
        assert len(self._instance.tasks) == 7
        assert isinstance(self._instance.tasks, Sequence)
        assert isinstance(self._instance.tasks[0], Task)

    def test_tasks_property_return_value_has_tasks_only(self) -> None:
        """
        :attr:`pipe.tasks` should return the ``Sequence`` of ``Task`` instances
        that comprise the ``pipe``. This should be ``Task`` instances
        regardless of whether the original callable was a ``Task``.
        """
        for _task in self._instance.tasks:
            assert isinstance(_task, Task)


class TestTask(TestCase):
    """Tests of the :class:`Task` interface default method implementations."""

    def test_of_callable_fails_on_none_input_value(self) -> None:
        """
        :meth:`Task.of_callable` should raise a :exc:`ValueError` when given a
        ``None`` callable as input.
        """
        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            Task.of_callable(source_callable=None)  # type: ignore

        assert exc_info.value.args[0] == "'source_callable' MUST not be None."

    def test_of_callable_method_returns_expected_value(self) -> None:
        """
        :meth:`Task.of_callable` should return a new ``Task`` instance wrapping
        the given callable.
        """
        add_100: Callable[[int], int] = partial(operator.add, 100)
        multiply_by_10: Callable[[int], int] = partial(operator.mul, 10)

        task1: Task[int, int] = Task.of_callable(add_100)
        task2: Task[int, int] = Task.of_callable(multiply_by_10)

        assert add_100(-100) == task1(-100) == 0
        assert multiply_by_10(100) == task2(100) == 1000
