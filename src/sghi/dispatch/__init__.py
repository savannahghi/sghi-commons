"""Multiple-producer-multiple-accept signal-dispatching *heavily* inspired by
`PyDispatcher <https://grass.osgeo.org/grass83/manuals/libpython/pydispatch.html>`_
and :doc:`Django dispatch<django:topics/signals>`
"""

from __future__ import annotations

import logging
import weakref
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from logging import Logger
from threading import RLock
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeGuard,
    TypeVar,
    final,
)

from ..utils import (
    ensure_instance_of,
    ensure_not_none,
    ensure_optional_instance_of,
    ensure_predicate,
    type_fqn,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

# =============================================================================
# TYPES
# =============================================================================


_ST_contra = TypeVar("_ST_contra", bound="Signal", contravariant=True)

Receiver = Callable[[_ST_contra], None]
"""
A `Receiver` is a callable object that accepts and processes
:class:`signals<Signal>`. It should accept a ``Signal`` as its sole argument
and return ``None``.
"""


# =============================================================================
# INTERFACES
# =============================================================================


class Signal(metaclass=ABCMeta):
    """An occurrence of interest.

    This class serves as a base for defining custom ``Signal`` classes that
    represent specific occurrences or events in an application.
    """

    __slots__ = ()


class Dispatcher(metaclass=ABCMeta):
    """An abstract class defining the interface for a :class:`Signal`
    dispatcher.

    ``Signal`` dispatchers are responsible for connecting and disconnecting
    :class:`receivers<Receiver>` to signals of interest, as well as sending
    signals to the registered receivers.

    Receivers can be connected or disconnected to signals using the
    :meth:`connect` and :meth:`disconnect` methods respectively. Once signals
    occur, connected receivers can be notified using the :meth:`send` method.
    New ``Dispatcher`` instances can be created using the :meth:`of` static
    factory method.

    .. tip::

        Unless otherwise indicated, at runtime, there should be an instance of
        this class at :attr:`sghi.app.dispatcher` ment to hold the main
        ``Dispatcher`` for the executing application.
    """

    __slots__ = ()

    @abstractmethod
    def connect(
        self,
        signal_type: type[_ST_contra],
        receiver: Receiver[_ST_contra],
        *,
        weak: bool = True,
    ) -> None:
        """Register a :class:`receiver<Receiver>` to be notified of occurrences
        of the specific :class:`signal type<Signal>`.

        :param signal_type: The type of ``Signal`` to connect the receiver to.
        :param receiver: The ``Receiver`` function to connect.
        :param weak: Whether to use weak references for the connection.
            Defaults to ``True``.

        :return: None.
        """
        ...

    @abstractmethod
    def disconnect(
        self,
        signal_type: type[_ST_contra],
        receiver: Receiver[_ST_contra],
    ) -> None:
        """Detach a :class:`Receiver` function from a specific :class:`Signal`
        type.

        .. admonition:: **To Implementors**
            :class: note

            The disconnect should detach the ``Receiver`` from this
            ``Dispatcher`` regardless of whether the ``Receiver`` was connected
            using weak references.

        :param signal_type: The type of ``Signal`` to disconnect the receiver
            from.
        :param receiver: The ``Receiver`` function to disconnect.

        :return: None.
        """
        ...

    @abstractmethod
    def send(self, signal: Signal, robust: bool = True) -> None:
        """Send a :class:`Signal` to all :class:`receivers<Receiver>`
        connected/registered to receive signals of the given signal type.

        If robust is set to ``False`` and a ``Receiver`` raises an error, the
        error propagates back through send, terminating the dispatch loop. So
        it's possible that all receivers won't be called if an error is raised.

        :param signal: The ``Signal`` to send.
        :param robust: Whether to handle errors robustly. Defaults to ``True``.

        :return: None.
        """
        ...

    @staticmethod
    def of() -> Dispatcher:
        """Create and return a new :class:`Dispatcher` instance.

        .. admonition:: Info

            The returned ``Dispatcher`` is threadsafe and uses weak references
            on :class:`receivers<Receiver>` by default. This can be changed by
            setting the ``weak`` parameter to ``False`` on the :meth:`connect`
            method when registering a new receiver.

        :return: A ``Dispatcher`` instance.
        """
        return _DispatcherImp()

    @staticmethod
    def of_proxy(
        source_dispatcher: Dispatcher | None = None,
    ) -> DispatcherProxy:
        """Create a :class:`DispatcherProxy` instance that wraps the given
        ``Dispatcher`` instance.

        If ``source_dispatcher`` is not given, it defaults to a value with
        similar semantics to those returned by the :meth:`Dispatcher.of`
        factory method.

        :param source_dispatcher: An optional ``Dispatcher`` instance to be
            wrapped by the returned ``DispatcherProxy`` instance. A default
            will be provided if not specified.

        :return: A ``DispatcherProxy`` instance.
        """
        return DispatcherProxy(
            source_dispatcher or Dispatcher.of(),
        )


# =============================================================================
# DECORATORS
# =============================================================================


class connect(Generic[_ST_contra]):  # noqa :N801
    """A decorator for registering :class:`receivers<Receiver>` to be notified
    when :class:`signals<Signal>` occur.

    This decorator simplifies the process of connecting a receiver function to
    a specific signal type in a :class:`dispatcher<Dispatcher>`. It is used to
    mark a function as a receiver and specify the associated signal type and
    dispatcher.
    """

    __slots__ = ("_signal_type", "_dispatcher", "_weak")

    def __init__(
        self,
        signal_type: type[_ST_contra],
        *,
        dispatcher: Dispatcher | None = None,
        weak: bool = True,
    ) -> None:
        """Initialize a new instance of ``connect`` decorator.

        :param signal_type: The type of ``Signal`` to connect the receiver to.
        :param dispatcher: The ``Dispatcher`` instance to connect the receiver
            in. If not provided, will default to the value of
            :attr:`sghi.app.dispatcher`.
        :param weak: Whether to use weak references for the connection.
            Defaults to ``True``.
        """
        super().__init__()
        from sghi.app import dispatcher as app_dispatcher

        ensure_instance_of(value=signal_type, klass=type)
        self._signal_type: type[_ST_contra] = signal_type
        self._dispatcher: Dispatcher = (
            ensure_optional_instance_of(
                value=dispatcher,
                klass=Dispatcher,
            )
            or app_dispatcher
        )
        self._weak: bool = weak

    def __call__(self, f: Receiver[_ST_contra]) -> Receiver[_ST_contra]:
        """Attach a :class:`receiver<Receiver>` function to a
        :class:`Dispatcher`.

        :param f: The function to be attached to a ``Dispatcher``.

        :return: The decorated function.
        """
        ensure_not_none(f, "'f' MUST not be None.")

        self._dispatcher.connect(self._signal_type, f, weak=self._weak)

        return f


# =============================================================================
# DISPATCH IMPLEMENTATIONS
# =============================================================================


@final
class DispatcherProxy(Dispatcher):
    """A :class:`Dispatcher` implementation that wraps other ``Dispatcher``
    instances.

    The main advantage is it allows for substitutions of ``Dispatcher`` values
    without requiring references to a ``Dispatcher`` instance to change.
    Changes to the wrapped ``Dispatcher`` instance can be made using the
    :meth:`set_source` method.
    """

    __slots__ = ("_source_dispatcher",)

    def __init__(self, source_dispatcher: Dispatcher) -> None:
        """Initialize a new :class:`DispatcherProxy` instance that wraps the
        given source ``Dispatcher`` instance.

        :param source_dispatcher: The ``Dispatcher`` instance to wrap. This
            MUST be an instance of ``Dispatcher``.

        :raise TypeError: If ``source_dispatcher`` is not an instance of
            ``Dispatcher``.
        """
        self._source_dispatcher: Dispatcher = ensure_instance_of(
            value=source_dispatcher,
            klass=Dispatcher,
        )

    def connect(
        self,
        signal_type: type[_ST_contra],
        receiver: Receiver[_ST_contra],
        *,
        weak: bool = True,
    ) -> None:
        self._source_dispatcher.connect(signal_type, receiver, weak=weak)

    def disconnect(
        self,
        signal_type: type[_ST_contra],
        receiver: Receiver[_ST_contra],
    ) -> None:
        self._source_dispatcher.disconnect(signal_type, receiver)

    def send(self, signal: Signal, robust: bool = True) -> None:
        self._source_dispatcher.send(signal, robust)

    def set_source(self, source_dispatcher: Dispatcher) -> None:
        """Change the :class:`dispatcher<Dispatcher>` instance wrapped by this
        proxy.

        :param source_dispatcher: The new source dispatcher to use. This MUST
            be an instance of ``Dispatcher``.

        :return: None.

        :raise TypeError: If ``source_dispatcher`` is not an instance of
            ``Dispatcher``.
        """
        self._source_dispatcher = ensure_instance_of(
            value=source_dispatcher,
            klass=Dispatcher,
        )


@final
class _DispatcherImp(Dispatcher):
    """The default implementation of the :class:`Dispatcher` interface."""

    __slots__ = ("_receivers", "_lock", "_logger", "_has_dead_receivers")

    def __init__(self) -> None:
        super().__init__()
        self._receivers: dict[
            type[Signal],
            set[Receiver | weakref.ReferenceType[Receiver]],
        ] = {}
        self._lock: RLock = RLock()
        self._logger: Logger = logging.getLogger(type_fqn(self.__class__))
        self._has_dead_receivers: bool = False

    def connect(
        self,
        signal_type: type[_ST_contra],
        receiver: Receiver[_ST_contra],
        *,
        weak: bool = True,
    ) -> None:
        ensure_instance_of(
            value=signal_type,
            klass=type,
            message="'signal_type' MUST be a type.",
        )
        ensure_predicate(
            issubclass(signal_type, Signal),
            message=(
                f"'signal_type' MUST be a subclass of '{type_fqn(Signal)}'."
            ),
            exc_factory=TypeError,
        )
        ensure_not_none(receiver, "'receiver' MUST not be None.")
        self._logger.debug("Connect receiver, '%s'.", type_fqn(receiver))
        _receiver: (
            Receiver[_ST_contra] | weakref.ReferenceType[Receiver[_ST_contra]]
        )
        _receiver = receiver
        if weak:
            ref = weakref.ref
            receiver_object = receiver
            # Check for bound methods
            if hasattr(receiver, "__self__") and hasattr(receiver, "__func__"):
                ref = weakref.WeakMethod
                receiver_object = receiver.__self__
            _receiver = ref(receiver)
            weakref.finalize(receiver_object, self._mark_dead_receiver_present)
        with self._lock:
            self._clear_dead_receivers()
            self._receivers.setdefault(signal_type, set()).add(_receiver)

    def disconnect(
        self,
        signal_type: type[_ST_contra],
        receiver: Receiver[_ST_contra],
    ) -> None:
        ensure_instance_of(
            value=signal_type,
            klass=type,
            message="'signal_type' MUST be a type.",
        )
        ensure_predicate(
            issubclass(signal_type, Signal),
            message=(
                f"'signal_type' MUST be a subclass of '{type_fqn(Signal)}'."
            ),
            exc_factory=TypeError,
        )
        ensure_not_none(receiver, "'receiver' MUST not be None.")
        self._logger.debug("Disconnect receiver, '%s'.", type_fqn(receiver))
        with self._lock:
            self._clear_dead_receivers()
            receivers = self._receivers.get(signal_type, set())
            receivers.discard(receiver)
            # Remove the receiver even if it was connected "weakly".
            weak_receivers: set[weakref.ReferenceType[Receiver[_ST_contra]]]
            weak_receivers = {  # pragma: no cover #  See: https://github.com/pytest-dev/pytest/issues/3689
                _receiver
                for _receiver in filter(self._is_weak, receivers)
                if _receiver() == receiver
            }
            receivers.difference_update(weak_receivers)

    def send(self, signal: Signal, robust: bool = True) -> None:
        ensure_instance_of(signal, Signal)
        for receiver in self._live_receivers(type(signal)):
            try:
                receiver(signal)
            except Exception:
                if not robust:
                    raise
                self._logger.exception(
                    "Error executing receiver '%s'.",
                    type_fqn(receiver),
                )

    def _clear_dead_receivers(self) -> None:
        with self._lock:
            if not self._has_dead_receivers:
                return
            for _signal_type, _receivers in self._receivers.items():
                self._receivers[_signal_type].difference_update(
                    set(filter(self._is_dead, _receivers)),
                )
            self._has_dead_receivers = False

    def _live_receivers(
        self,
        signal_type: type[_ST_contra],
    ) -> Iterable[Receiver[_ST_contra]]:
        with self._lock:
            self._clear_dead_receivers()
            receivers: set[
                Receiver[_ST_contra]
                | weakref.ReferenceType[Receiver[_ST_contra]]
            ]
            receivers = self._receivers.get(signal_type, set())
            return filter(
                self._is_live,
                map(self._dereference_as_necessary, receivers),
            )

    def _mark_dead_receiver_present(self) -> None:
        with self._lock:
            self._has_dead_receivers = True

    @staticmethod
    def _dereference_as_necessary(
        receiver: Receiver[_ST_contra]
        | weakref.ReferenceType[Receiver[_ST_contra]],
    ) -> Receiver[_ST_contra] | None:
        # Dereference, if weak reference
        return (
            receiver()
            if isinstance(receiver, weakref.ReferenceType)
            else receiver
        )

    @staticmethod
    def _is_dead(receiver: Receiver | weakref.ReferenceType) -> bool:
        r = receiver
        return isinstance(r, weakref.ReferenceType) and r() is None

    @staticmethod
    def _is_live(
        receiver: Receiver[_ST_contra] | None,
    ) -> TypeGuard[Receiver[_ST_contra]]:
        return receiver is not None

    @staticmethod
    def _is_weak(
        receiver: Receiver[_ST_contra]
        | weakref.ReferenceType[Receiver[_ST_contra]],
    ) -> TypeGuard[weakref.ReferenceType[Receiver[_ST_contra]]]:
        return isinstance(receiver, weakref.ReferenceType)


# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = [
    "Dispatcher",
    "DispatcherProxy",
    "Receiver",
    "Signal",
    "connect",
]
