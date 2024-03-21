"""``Registry`` interface definition, implementing classes and helpers."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Any, final

from sghi.dispatch import Dispatcher, Signal
from sghi.exceptions import SGHIError
from sghi.utils import ensure_instance_of, ensure_not_none

# =============================================================================
# EXCEPTIONS
# =============================================================================


class NoSuchRegistryItemError(SGHIError, LookupError):
    """Non-existent :class:`Registry` item access error.

    This is raised when trying to access or delete an item that does not exist
    in a ``Registry``.
    """

    def __init__(self, item_key: str, message: str | None = None) -> None:
        """Initialize a ``NoSuchRegistryItemError`` with the given properties.

        :param item_key: The key of the missing item.
        :param message: An optional message for the resulting exception.
            If none is provided, then a generic one is automatically generated.
        """
        self._item_key: str = ensure_not_none(
            item_key,
            "'item_key' MUST not be None.",
        )
        super().__init__(
            message=message
            or (
                "Item with key '%s' does not exist in the registry."
                % self._item_key
            ),
        )

    @property
    def item_key(self) -> str:
        """Return the missing item's key whose attempted access resulted in
        this exception being raised.

        :return: The missing item's key.
        """
        return self._item_key


# =============================================================================
# SIGNALS
# =============================================================================


@dataclass(frozen=True, slots=True, match_args=True)
class RegistryItemRemoved(Signal):
    """Signal indicating the removal of an item from the :class:`Registry`.

    This signal is emitted when an item is removed from the ``Registry``.
    """

    item_key: str = field()
    """The key of the removed item."""


@dataclass(frozen=True, slots=True, match_args=True)
class RegistryItemSet(Signal):
    """Signal indicating the setting of an item in the :class:`Registry`.

    This signal is emitted when a new item is added or updated to the
    ``Registry``.
    """

    item_key: str = field()
    """The key of the set item."""

    item_value: Any = field(repr=False)
    """The value of the added item."""


# =============================================================================
# REGISTRY INTERFACE
# =============================================================================


class Registry(metaclass=ABCMeta):
    """An interface representing a registry for storing key-value pairs.

    A ``Registry`` allows for storage and retrieval of values using unique
    keys. It supports basic dictionary-like operations and provides an
    interface for interacting with registered items.

    A ``Registry`` also comes bundled with a :class:`~sghi.dispatch.Dispatcher`
    whose responsibility is to emit :class:`signals<Signal>` whenever changes
    to the registry are made. It allows other components to subscribe to these
    signals and react accordingly. This dispatcher is accessible using the
    :attr:`~sghi.registry.Registry.dispatcher` property.

    For a list of supported signals, see the
    :attr:`~sghi.registry.Registry.dispatcher` property docs.

    .. tip::

        Unless otherwise indicated, at runtime, there should be an instance of
        this class at :attr:`sghi.app.registry` ment to hold the main
        ``Registry`` for the executing application/tool.
    """

    __slots__ = ()

    @abstractmethod
    def __contains__(self, key: str) -> bool:
        """Check if the registry contains an item with the specified key.

        :param key: The key to check for.

        :return: ``True`` if the key exists in the registry, ``False``
            otherwise.
        """
        ...

    @abstractmethod
    def __delitem__(self, key: str) -> None:
        """Remove an item from the registry using the specified key.

        If successful, this will result in a :class:`RegistryItemRemoved`
        signal being emitted.

        :param key: The key of the item to remove.

        :return: None.

        :raises NoSuchRegistryItemError: If the key does not exist in the
            registry.
        """
        ...

    @abstractmethod
    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        """
        Retrieve the value associated with the specified key from the registry.

        :param key: The key of the item to retrieve.

        :return: The value associated with the key.

        :raises NoSuchRegistryItemError: If the key does not exist in the
            registry.
        """
        ...

    @abstractmethod
    def __setitem__(self, key: str, value: Any) -> None:  # noqa: ANN401
        """Set the value associated with the specified key in the registry.

        If successful, this will result in a :class:`RegistryItemSet`
        signal being emitted.

        :param key: The key of the item to set.
        :param value: The value to associate with the key.

        :return: None.
        """
        ...

    @property
    @abstractmethod
    def dispatcher(self) -> Dispatcher:
        """Get the :class:`~sghi.dispatch.Dispatcher` associated with the
        ``Registry``.

        The dispatcher is responsible for emitting signals when items are added
        or removed from the registry. It allows other components to subscribe
        to these signals and react accordingly.

        ----

        **Supported Signals**

        Each ``Registry`` implementation should at the very least support the
        following signals:

        - :class:`RegistryItemSet` - This signal is emitted when either a new
          item is added to the ``Registry``, or an existing item updated. It
          includes information about the item's key and value.
        - :class:`RegistryItemRemoved` - This signal is emitted when an item is
          removed from the registry. It includes information about the item's
          key.

        These signals provide a way for other parts of the application to react
        to changes in the registry, making the system more dynamic and
        responsive.


        :return: The dispatcher instance associated with the registry.
        """
        ...

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """Retrieve the value associated with the specified key from the
        ``Registry``, with an optional default value if the key does not exist.

        :param key: The key of the item to retrieve.

        :param default: The default value to return if the key does not exist.
            Defaults to ``None`` when not specified.

        :return: The value associated with the key, or the default value.
        """
        ...

    @abstractmethod
    def pop(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """Remove and return the value associated with the specified key from
        the ``Registry``, or the specified default if the key does not exist.

        .. note::

            A :class:`RegistryItemRemoved` signal will only be emitted
            `if and only if` an item with the specified key existed in the
            ``Registry`` and was thus removed.

        :param key: The key of the item to remove.
        :param default: The default value to return if the key does not exist.
            Defaults to ``None`` when not specified.

        :return: The value associated with the key, or the default value.
        """
        ...

    @abstractmethod
    def setdefault(self, key: str, value: Any) -> Any:  # noqa: ANN401
        """Retrieve the value associated with the specified key from the
        ``Registry``, or set it if the key does not exist.

        .. note::

            A :class:`RegistryItemSet` signal will only be emitted
            `if and only if` an item with the specified key does not exist in
            the ``Registry`` and thus the new default value was set.

        :param key: The key of the item to retrieve or set.
        :param value: The value to associate with the key if it does not exist.

        :return: The value associated with the key, or the newly set value.
        """
        ...

    @staticmethod
    def of(dispatcher: Dispatcher | None = None) -> Registry:
        """Factory method to create ``Registry`` instances.

        :param dispatcher: An optional ``Dispatcher`` instance to associate
            with the registry. A new ``Dispatcher`` instance will be created if
            not specified.

        :return: A ``Registry`` instance.
        """
        return _RegistryImp(dispatcher=dispatcher or Dispatcher.of())

    @staticmethod
    def of_proxy(source_registry: Registry | None = None) -> RegistryProxy:
        """Create a :class:`RegistryProxy` instance that wraps the given
        ``Registry`` instance.

        If ``source_registry`` is not given, it defaults to a value with
        similar semantics to those returned by the :meth:`Registry.of` factory
        method.

        :param source_registry: An optional ``Registry`` instance to be wrapped
            by the returned ``RegistryProxy`` instance. A default will be
            provided if not specified.

        :return: A ``RegistryProxy`` instance.
        """
        return RegistryProxy(source_registry or Registry.of())


# =============================================================================
# REGISTRY IMPLEMENTATIONS
# =============================================================================


@final
class RegistryProxy(Registry):
    """
    A :class:`Registry` implementation that wraps other ``Registry`` instances.

    The main advantage is it allows for substitutions of ``Registry`` values
    without requiring references to a ``Registry`` instance to change. Changes
    to the wrapped ``Registry`` instance can be made using the
    :meth:`set_source` method.
    """

    __slots__ = ("_source_registry",)

    def __init__(self, source_registry: Registry) -> None:
        """
        Initialize a new :class:`RegistryProxy` instance that wraps the given
        source ``Registry`` instance.

        :param source_registry: The ``Registry`` instance to wrap. This MUST be
            an instance of ``Registry``.

        :raise TypeError: If ``source_registry`` is not an instance of
            ``Registry``.
        """
        super().__init__()
        self._source_registry: Registry = ensure_instance_of(
            value=source_registry,
            klass=Registry,
        )

    def __contains__(self, key: str) -> bool:
        return self._source_registry.__contains__(key)

    def __delitem__(self, key: str) -> None:
        self._source_registry.__delitem__(key)

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        return self._source_registry.__getitem__(key)

    def __setitem__(self, key: str, value: Any) -> None:  # noqa: ANN401
        self._source_registry.__setitem__(key, value)

    @property
    def dispatcher(self) -> Dispatcher:
        return self._source_registry.dispatcher

    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        return self._source_registry.get(key, default=default)

    def pop(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        return self._source_registry.pop(key, default=default)

    def setdefault(self, key: str, value: Any) -> Any:  # noqa: ANN401
        return self._source_registry.setdefault(key, value)

    def set_source(self, source_registry: Registry) -> None:
        """
        Change the :class:`registry<Registry>` instance wrapped by this proxy.

        :param source_registry: The new source registry to use. This MUST be an
            instance of ``Registry``.

        :return: None.

        :raise TypeError: If ``source_registry`` is not an instance of
            ``Registry``.
        """
        self._source_registry = ensure_instance_of(source_registry, Registry)


@final
class _RegistryImp(Registry):
    """An implementation of the Registry interface."""

    __slots__ = ("_dispatcher", "_items")

    def __init__(self, dispatcher: Dispatcher) -> None:
        super().__init__()
        self._dispatcher: Dispatcher = ensure_instance_of(
            value=dispatcher,
            klass=Dispatcher,
        )
        self._items: dict[str, Any] = {}

    def __contains__(self, key: str) -> bool:
        return key in self._items

    def __delitem__(self, key: str) -> None:
        ensure_not_none(key, "'key' MUST not be None.")
        try:
            del self._items[key]
            self.dispatcher.send(RegistryItemRemoved(item_key=key))
        except KeyError:
            raise NoSuchRegistryItemError(item_key=key) from None

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        ensure_not_none(key, "'key' MUST not be None.")
        try:
            return self._items[key]
        except KeyError:
            raise NoSuchRegistryItemError(item_key=key) from None

    def __setitem__(self, key: str, value: Any) -> None:  # noqa: ANN401
        ensure_not_none(key, "'key' MUST not be None.")
        self._items[key] = value
        self.dispatcher.send(
            RegistryItemSet(item_key=key, item_value=value),
        )

    @property
    def dispatcher(self) -> Dispatcher:
        return self._dispatcher

    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        ensure_not_none(key, "'key' MUST not be None.")
        return self._items.get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        ensure_not_none(key, "'key' MUST not be None.")
        try:
            value = self._items.pop(key)
            self._dispatcher.send(RegistryItemRemoved(item_key=key))
            return value
        except KeyError:
            return default

    def setdefault(self, key: str, value: Any) -> Any:  # noqa: ANN401
        ensure_not_none(key, "'key' MUST not be None.")
        try:
            return self[key]
        except LookupError:
            self[key] = value
            return value


# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = (
    "NoSuchRegistryItemError",
    "Registry",
    "RegistryItemRemoved",
    "RegistryItemSet",
    "RegistryProxy",
)
