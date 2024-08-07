"""``Task`` interface definition together with its common implementations."""

from __future__ import annotations

import warnings
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterable, MutableSequence, Sequence
from concurrent.futures import (
    ALL_COMPLETED,
    Executor,
    Future,
    ThreadPoolExecutor,
    wait,
)
from functools import cache, reduce, update_wrapper
from logging import Logger, getLogger
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, final, overload

from typing_extensions import deprecated, override

from ..disposable import Disposable, ResourceDisposedError
from ..disposable import not_disposed as _nd_factory
from ..utils import (
    ensure_callable,
    ensure_instance_of,
    ensure_not_none,
    ensure_not_none_nor_empty,
    type_fqn,
)

if TYPE_CHECKING:
    from typing import Self

# =============================================================================
# TYPES
# =============================================================================


_IT = TypeVar("_IT")
_IT1 = TypeVar("_IT1")
_OT = TypeVar("_OT")
_OT1 = TypeVar("_OT1")


# =============================================================================
# HELPERS
# =============================================================================


def _callables_to_tasks_as_necessary(
    tasks: Sequence[Task[_IT, _OT] | Callable[[_IT], _OT]],
) -> Sequence[Task[_IT, _OT]]:
    """Convert callables to :class:`Task` instances if necessary.

    The given callables should accept a single parameter of type ``IT`` and
    return a value of type ``OT``. Instances of ``Tasks`` in the given
    ``Sequence`` will be returned as is.

    :param tasks: A ``Sequence`` of ``Task`` instances or callables.

    :return: A ``Sequence`` of ``Task`` instances.

    :raises ValueError: If `tasks` is ``None``.
    """
    ensure_not_none(tasks, "'tasks' MUST not be None.")
    return tuple(
        task if isinstance(task, Task) else _OfCallable(task) for task in tasks
    )


def task(f: Callable[[_IT], _OT]) -> Task[_IT, _OT]:
    """Mark/Decorate a callable object as a :class:`~sghi.task.Task`.

    .. important::

        The decorated callable *MUST* accept at least one argument but have
        at *MOST* one required argument.

    :param f: The callable object to be decorated. The callable *MUST* accept
        at least one argument but have at *MOST* one required argument.

    :return: A ``Task`` instance that wraps the given callable object.

    :raise ValueError: If the given value is NOT a callable.
    """
    ensure_callable(f, message="A callable object is required.")

    return _OfCallable(source_callable=f)


# =============================================================================
# EXCEPTIONS
# =============================================================================


class ConcurrentExecutorDisposedError(ResourceDisposedError):
    """
    Indicates that an erroneous usage of a disposed :class:`ConcurrentExecutor`
    was made.
    """

    def __init__(self, message: str | None = "ConcurrentExecutor disposed."):
        """Initialize a ``ConcurrentExecutorDisposedError`` with an optional
        message.

        :param message: An optional message for the exception.
        """
        super().__init__(message=message)


# =============================================================================
# TASK INTERFACE
# =============================================================================


class Task(Generic[_IT, _OT], metaclass=ABCMeta):
    """A job or action to perform.

    An interface that describes a job or action to be performed. The interface
    defines a single abstract method :meth:`execute`, that accepts a single
    input value and returns a result. A `Task` instance can also be used as a
    callable, the actual call is delegated to the ``execute`` method.

    ``Task`` instances can be composed using the ``<<`` and ``>>`` operators.
    The resulting compositions have the same effect as the :meth:`compose` and
    :meth:`and_then` methods respectively.
    """

    __slots__ = ()

    def __call__(self, an_input: _IT) -> _OT:
        """Perform a computation given an input and return a result.

        Call the ``Task`` as a callable. Delegate actual call to
        :meth:`execute`.

        :param an_input: An input to the tasks.

        :return: The result of the computation.
        """
        return self.execute(an_input)

    def __lshift__(self, __before: Task[_IT1, _IT], /) -> Task[_IT1, _OT]:
        """Compose two :class:`tasks<sghi.task.Task>` together.

        This operator creates a new task that performs the computation of the
        right operand (``__before``) before the computation of the left operand
        (``self``). In other words, the output of the right operand becomes
        the input to the left operand.

        .. versionadded:: 1.4

        :param __before: The task to be executed prior to ``self``. This MUST
            be a ``Task`` instance.

        :return: A new ``Task`` that combines the computations of ``__before``
            and ``self`` in that order.

        .. seealso:: :meth:`~sghi.task.Task.compose`.
        """
        return (
            self.compose(__before)
            if isinstance(__before, Task)
            else NotImplemented
        )

    def __rshift__(self, __after: Task[_OT, _OT1], /) -> Task[_IT, _OT1]:
        """Chain two :class:`tasks<sghi.task.Task>` together.

        This operator creates a new task that performs the computation of the
        right operand (``__after``) after the computation of the left operand
        (``self``). In other words, the output of left becomes the input to
        ``__after``.

        .. versionadded:: 1.4

        :param __after: The task to chain to ``self``. This MUST be a ``Task``
            instance.

        :return: A new ``Task`` that combines the computations of ``self`` and
            ``__after`` in that order.

        .. seealso:: :meth:`~sghi.task.Task.and_then`.
        """
        return (
            self.and_then(__after)
            if isinstance(__after, Task)
            else NotImplemented
        )

    @abstractmethod
    def execute(self, an_input: _IT) -> _OT:
        """Perform a computation given an input and return a result.

        :param an_input: An input to the task.

        :return: The result of the computation.
        """
        ...

    def and_then(self, after: Task[_OT, _OT1]) -> Task[_IT, _OT1]:
        """Chain two :class:`tasks<sghi.task.Task>` together.

        Return a new ``Task`` that performs the computation of the given
        task after the computation of this task. The returned task first
        :meth:`applies<execute>` this task to its input, and then applies the
        ``after`` task to the result. That is, the out output of
        ``self.execute()`` becomes the input to ``after.execute()``.

        .. versionadded:: 1.4

        :param after: The task to be executed following this one. This MUST be
            a ``Task`` instance.

        :return: A new ``Task`` that combines the computations of this task
            and the given one in that order.

        :raise ValueError: If ``after`` is NOT a ``Task`` instance.

        .. seealso:: :meth:`~sghi.task.Task.compose`.
        """
        ensure_instance_of(
            value=after,
            klass=Task,
            message="'after' MUST be an 'sghi.task.Task' instance.",
        )

        def _do_chain(an_input: _IT) -> _OT1:
            return after.execute(self.execute(an_input))

        return _OfCallable(_do_chain)

    def compose(self, before: Task[_IT1, _IT]) -> Task[_IT1, _OT]:
        """Compose two :class:`tasks<sghi.task.Task>` together.

        Return a new ``Task`` that performs the computation of the given
        task before the computation of this task. The returned task first
        :meth:`applies<execute>` the ``before`` task to its input, and then
        applies this task to the result. That is, the output of
        ``before.execute()`` becomes the input to ``self.execute()``.

        .. versionadded:: 1.4

        :param before: The task to be executed prior to this one. This MUST be
            a ``Task`` instance.

        :return: A new ``Task`` that combines the computations of the given
            task and this one in that order.

        :raise ValueError: If ``before`` is NOT a ``Task`` instance.

        .. seealso:: :meth:`~sghi.task.Task.and_then`.
        """
        ensure_instance_of(
            value=before,
            klass=Task,
            message="'before' MUST be an 'sghi.task.Task' instance.",
        )

        def _do_compose(an_input: _IT1) -> _OT:
            return self.execute(before.execute(an_input))

        return _OfCallable(_do_compose)

    @staticmethod
    def of_callable(source_callable: Callable[[_IT], _OT]) -> Task[_IT, _OT]:
        """Create a :class:`~sghi.task.Task` instance from a callable.

        .. important::

            The given callable *MUST* accept at least one argument but have
            at *MOST* one required argument.

        :param source_callable: The callable function to wrap as a ``Task``.
            This *MUST* accept at least one argument but have at *MOST* one
            required argument.

        :return: A ``Task`` instance.

        :raises ValueError: If ``source_callable`` is NOT a callable.

        .. seealso:: :func:`@task<sghi.task.task>` decorator.
        """
        # FIXME: rename 'source_callable' to 'target_callable' instead.
        return _OfCallable(source_callable=source_callable)

    @staticmethod
    @cache
    def of_identity() -> Task[_IT, _IT]:
        """Return a  :class:`~sghi.task.Task` that always returns its input.

        The returned ``Task`` always returns its input argument as is.

        .. note::

            The instances returned by this method are NOT guaranteed to be
            distinct on each invocation.

        :return: A ``Task`` instance that always returns its input argument
            as is.
        """
        return _OfCallable(source_callable=lambda _v: _v)


# =============================================================================
# COMMON IMPLEMENTATIONS
# =============================================================================


@final
class Chain(Task[Callable[[_IT], Any], "Chain[Any]"], Generic[_IT]):
    """
    A :class:`Task` that wraps a value and applies a transformation (or series
    of transformations) on the value.

    The output of each transformation is wrapped in a new ``Chain`` instance,
    facilitating the chaining together of multiple transformations. This
    capability can be employed to compose complex transformations from smaller
    ones.

    The wrapped value can be retrieved using the :attr:`value` property.
    """

    __slots__ = ("_value",)

    def __init__(self, value: _IT) -> None:
        """Initialize a new :class:`Chain` instance that wraps the given value.

        :param value: The value to wrap and apply transformations to.
        """
        super().__init__()
        self._value: _IT = value

    def __add__(self, __an_input: Callable[[_IT], _OT], /) -> Chain[_OT]:
        return self.execute(an_input=__an_input)

    @property
    def value(self) -> _IT:
        """Return the wrapped value.

        :return: The wrapped value.
        """
        return self._value

    @override
    def execute(self, an_input: Callable[[_IT], _OT]) -> Chain[_OT]:
        """Perform the given transformation on the wrapped value and wrap the
        result in a new ``Chain`` instance.

        :param an_input: A callable defining a transformation to be applied to
            the wrapped value.

        :return: A new ``Chain`` instance that wraps the result of the given
            transformation.

        :raises ValueError: If the given transformation is NOT a callable.
        """
        bind: Callable[[_IT], _OT]
        bind = ensure_callable(an_input, "'an_input' MUST be a callable.")
        return Chain(bind(self._value))


@deprecated("To be removed in v2.x")
@final
class Consume(Task[_IT, _IT], Generic[_IT]):
    """A :class:`Task` that applies an action to its inputs.

    This ``Task`` wraps a callable and applies it to its input. It returns
    its input value as is on execution and is better suited for
    operations with side effects.

    .. deprecated:: 1.4
       To be removed in v2.
    """

    __slots__ = ("_accept",)

    def __init__(self, accept: Callable[[_IT], Any]) -> None:
        """Initialize a new :class:`Consume` instance that applies the given
        action to its inputs.

        :param accept: A callable to apply to this task's inputs. This MUST not
            be None.

        :raises ValueError: If the given callable is NOT a callable.
        """
        super().__init__()
        ensure_callable(accept, "'accept' MUST be a callable.")
        self._accept: Callable[[_IT], Any] = accept

    def __add__(self, __an_input: Callable[[_IT], Any], /) -> Consume[_IT]:  # type: ignore[reportDeprecated]
        return self.and_then(accept=__an_input)  # type: ignore[reportDeprecated]

    @overload
    def and_then(self, after: Task[_OT, _OT1]) -> Task[_IT, _OT1]: ...

    @deprecated("To be removed in v2.x")
    @overload
    def and_then(self, accept: Callable[[_IT], Any]) -> Consume[_IT]:  # type: ignore[reportDeprecated]
        ...

    def and_then(self, accept):  # type: ignore[reportDeprecated]
        """Compose this :class:`Consume` action with the provided action.

        This creates a new ``Consume`` instance that performs both this task's
        action and the provided action.

        .. deprecated:: 1.4
           To be removed in v2.

        :param accept: The action to compose with this task's action. This
            MUST be a callable object.

        :return: A new ``Consume`` instance that performs both actions.

        :raises ValueError: If ``accept`` is NOT a callable.
        """
        if isinstance(accept, Task):
            return super().and_then(accept)

        ensure_callable(accept, "'accept' MUST be a callable.")

        def _compose_accept(an_input: _IT) -> None:
            self._accept(an_input)
            accept(an_input)

        return Consume(accept=_compose_accept)  # type: ignore[reportDeprecated]

    @override
    def execute(self, an_input: _IT) -> _IT:
        self._accept(an_input)
        return an_input


@final
class Pipe(Task[_IT, _OT], Generic[_IT, _OT]):
    """A :class:`Task` that pipes its input through a ``Sequence`` of tasks.

    This ``Task`` applies a series of tasks to its input, passing the output of
    one ``Task`` as the input to the next.
    """

    __slots__ = ("_tasks",)

    def __init__(self, *tasks: Task[Any, Any] | Callable[[Any], Any]):
        """Create a new :class:`Pipe` instance of the given tasks.

        :param tasks: A ``Sequence`` of the tasks or callables to apply this
            pipe's inputs to. This MUST not be empty. If callables are given,
            they MUST accept at least one argument but have at MOST one
            required argument.

        :raises ValueError: If no tasks were specified, i.e. ``tasks`` is
            empty.
        """
        super().__init__()
        ensure_not_none_nor_empty(tasks, "'tasks' MUST not be None or empty.")
        self._tasks: Sequence[Task[Any, Any]]
        self._tasks = _callables_to_tasks_as_necessary(tasks)

    @property
    def tasks(self) -> Sequence[Task[Any, Any]]:
        """The ``Sequence`` of :class:`tasks <Task>` that comprise this pipe.

        :return: The tasks that comprise this pipe.
        """
        return self._tasks

    @override
    def execute(self, an_input: _IT) -> _OT:
        """
        Apply the given input to the :class:`tasks <Task>` that comprise this
        pipe, sequentially.

        The output of each task becomes the input of the next one. The result
        of the final ``Task`` is the output of this *pipe* operation.

        :param an_input: The input to start with.

        :return: The final output after applying all the tasks.
        """
        _acc: Any
        _tsk: Task[Any, Any]
        return cast(
            _OT,
            reduce(
                lambda _acc, _tsk: _tsk.execute(_acc),
                self.tasks[1:],
                self.tasks[0].execute(an_input),
            ),
        )


@final
class Supplier(Task[None, _OT], Generic[_OT]):
    """A specialized :class:`Task` that supplies/provides a result.

    This subclass of ``Task`` represents a task that provides a result without
    needing any input value. It wraps/decorates a callable that returns the
    desired output.

    .. versionadded:: 1.4
    """

    __slots__ = ("_source_callable", "__dict__")

    def __init__(self, source_callable: Callable[[], _OT]):
        """Create a ``Supplier`` instance that wraps the provided callable.

        :param source_callable: A callable object that takes no arguments and
            returns the desired result.

        :raise TypeError: If ``source_callable`` is not a callable object.
        """
        super().__init__()
        ensure_callable(
            source_callable,
            message="'source_callable' MUST be a callable object.",
        )
        self._source_callable: Callable[[], _OT]
        self._source_callable = source_callable
        update_wrapper(self, self._source_callable)

    @override
    def __call__(self, an_input: None = None) -> _OT:
        return self.execute()

    @override
    def execute(self, an_input: None = None) -> _OT:
        """Retrieve and return a result/value.

        This method overrides the base class ``execute`` and simply calls the
        wrapped callable to retrieve the result. Since this is a ``Supplier``,
        the argument to this method is ignored.

        :param an_input: Unused parameter. Defaults to ``None``. This is only
            here to maintain compatibility with the ``Task`` interface.

        :return: The retrieved/supplied result.
        """
        return self._source_callable()


chain = Chain

consume = Consume  # type: ignore[reportDeprecated]

pipe = Pipe

supplier = Supplier

supply = Supplier


# =============================================================================
# CONCURRENT EXECUTOR
# =============================================================================


not_disposed = _nd_factory(exc_factory=ConcurrentExecutorDisposedError)


@final
class ConcurrentExecutor(
    Task[_IT, Iterable[Future[_OT]]],
    Disposable,
    Generic[_IT, _OT],
):
    """
    A :class:`Task` that concurrently executes multiple `tasks` with a shared
    input.

    The output of these tasks is an :class:`Iterable` of
    :external+python:py:class:`futures<concurrent.futures.Future>`
    representing the execution of the given tasks. If the
    ``wait_for_completion`` constructor parameter is set to ``True``, the
    default, the :meth:`execute` method will block until all tasks have
    completed.

    .. important::

        When ``wait_for_completion`` is set to ``False``, instances of this
        class should not be used as context managers. This is because the
        underlying ``Executor`` will be shutdown immediately on exit of the
        ``with`` block. This will happen regardless of the completion status
        of the embedded tasks, leading to cancellations of those tasks, which
        might not be the intended behaviour.

    .. tip::

        By default, instances of this class use a
        :external+python:py:class:`~concurrent.futures.ThreadPoolExecutor`
        to run the tasks concurrently. This is suitable for short `I/O-bound`
        tasks. However, for compute-intensive tasks, consider using a
        :external+python:py:class:`~concurrent.futures.ProcessPoolExecutor` by
        passing it through the ``executor`` constructor parameter during
        initialization.

        For more details, see the official Python
        :doc:`concurrency docs <python:library/concurrent.futures>`.
    """

    __slots__ = (
        "_tasks",
        "_wait_for_completion",
        "_executor",
        "_is_disposed",
        "_logger",
    )

    def __init__(
        self,
        *tasks: Task[_IT, _OT] | Callable[[_IT], _OT],
        wait_for_completion: bool = True,
        executor: Executor | None = None,
    ):
        """Initialize a new ``ConcurrentExecutor`` instance with the given
        properties.

        :param tasks: The tasks or callables to be executed concurrently. This
            MUST not be ``None`` or empty. If callables are given, they MUST
            accept at least one argument but have at MOST one required
            argument.
        :param wait_for_completion: Whether ``execute`` should block and wait
            for all the given tasks to complete execution. Defaults to
            ``True``.
        :param executor: The :class:`executor <concurrent.futures.Executor>`
            instance to use when executing the tasks. If not provided, a
            ``ThreadPoolExecutor`` is used.

        :raises ValueError: If tasks is ``None`` or empty.
        """
        super().__init__()
        ensure_not_none_nor_empty(tasks, "'tasks' MUST not be None or empty.")
        self._tasks: Sequence[Task[_IT, _OT]]
        self._tasks = _callables_to_tasks_as_necessary(tasks)
        self._wait_for_completion: bool = wait_for_completion
        self._executor: Executor = executor or ThreadPoolExecutor()
        self._is_disposed: bool = False
        self._logger: Logger = getLogger(type_fqn(self.__class__))

    @not_disposed
    @override
    def __enter__(self) -> Self:
        super().__enter__()
        if not self._wait_for_completion:
            msg: str = (
                "Using instances of this class as a context manager when "
                "'wait_for_completion' is set to 'False' is discouraged."
            )
            warnings.warn(message=msg, stacklevel=3)
        return self

    @property
    @override
    def is_disposed(self) -> bool:
        return self._is_disposed

    @property
    def tasks(self) -> Sequence[Task[_IT, _OT]]:
        """
        Get the sequence of :class:`tasks<Task>` that will be executed
        concurrently.

        :return: The sequence of tasks.
        """
        return self._tasks

    @override
    def dispose(self) -> None:
        """
        Shutdown the underlying :class:`~concurrent.futures.Executor` powering
        this ``Task``.

        After this method returns successfully, the :attr:`is_disposed`
        property will always return ``True``.

        .. important::

            When ``wait_for_completion`` is set to ``True``, this method will
            wait for all scheduled tasks to complete before returning. If set
            to ``False``, this is not guaranteed, which might result in some
            tasks not being executed or being canceled.

        .. note::
            Unless otherwise specified, trying to use methods of this class
            decorated with the :func:`~sghi.disposable.not_disposed` decorator
            after this method returns is considered a programming error and
            will result in a :exc:`ConcurrentExecutorDisposedError` being
            raised.

            This method is idempotent allowing it to be called more than once;
            only the first call, however, has an effect.

        :return: None.
        """
        self._is_disposed = True
        self._executor.shutdown(wait=self._wait_for_completion)

    @not_disposed
    @override
    def execute(self, an_input: _IT) -> Iterable[Future[_OT]]:
        """Execute the tasks concurrently with the given input.

        .. note::

            If the ``wait_for_completion`` property is ``True``, this method
            will block until all tasks finish execution. If set to ``False``,
            all tasks will be scheduled for concurrent execution, after which
            this method will return immediately, regardless of whether all
            tasks have completed execution.

        :param an_input: The shared input to pass to each task.

        :return: An ``Iterable`` of futures representing the execution of each
            task.

        :raises ConcurrentExecutorDisposedError: If this executor is already
            disposed.
        """
        futures: Iterable[Future[_OT]] = reduce(
            lambda _partial, _tsk: self._accumulate(
                _partial,
                self._executor.submit(self._do_execute_task, _tsk, an_input),
            ),
            self.tasks,
            [],
        )
        if self._wait_for_completion:
            wait(futures, return_when=ALL_COMPLETED)
        return futures

    @staticmethod
    def _accumulate(
        scheduled_tasks: MutableSequence[Future[_OT]],
        new_submission: Future[_OT],
    ) -> MutableSequence[Future[_OT]]:
        scheduled_tasks.append(new_submission)
        return scheduled_tasks

    def _do_execute_task(self, task: Task[_IT, _OT], an_input: _IT) -> _OT:
        """Execute an individual :class:`Task` with the provided input.

        :param task: The ``Task`` to execute.
        :param an_input: The input to pass to the ``Task``.

        :return: The result of the task's execution.

        :raises Exception: If the execution failed.
        """
        try:
            result: _OT = task.execute(an_input)
        except Exception as exp:
            self._logger.error(
                "Error while executing tasks of type='%s'.",
                type_fqn(type(task)),
                exc_info=exp,
            )
            raise exp
        return result


execute_concurrently = ConcurrentExecutor


# =============================================================================
# FROM CALLABLE
# =============================================================================


@final
class _OfCallable(Task[_IT, _OT]):
    __slots__ = ("_source_callable", "__dict__")

    def __init__(self, source_callable: Callable[[_IT], _OT]):
        super().__init__()
        ensure_callable(
            source_callable,
            message="'source_callable' MUST be a callable object.",
        )
        self._source_callable: Callable[[_IT], _OT]
        self._source_callable = source_callable
        update_wrapper(self, self._source_callable)

    @override
    def execute(self, an_input: _IT) -> _OT:
        return self._source_callable(an_input)


# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = [
    "Chain",
    "ConcurrentExecutor",
    "ConcurrentExecutorDisposedError",
    "Consume",
    "Pipe",
    "Supplier",
    "Task",
    "chain",
    "consume",
    "execute_concurrently",
    "pipe",
    "supplier",
    "supply",
    "task",
]
