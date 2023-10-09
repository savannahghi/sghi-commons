from unittest import TestCase

import pytest

from sghi.dispatch import connect
from sghi.registry import (
    NoSuchRegistryItemError,
    Registry,
    RegistryItemRemoved,
    RegistryItemSet,
    RegistryProxy,
)


class TestRegistry(TestCase):
    """
    Tests of the :class:`Registry` interface default method implementations.
    """

    def test_of_factory_method_return_value(self) -> None:
        """:meth:`Registry.of` should return a ``Registry`` instance."""

        assert isinstance(Registry.of(), Registry)

    def test_of_proxy_factory_method_return_value(self) -> None:
        """
        :meth:`Registry.of_proxy` should return a ``RegistryProxy`` instance.
        """

        assert isinstance(RegistryProxy.of_proxy(), RegistryProxy)


class TestRegistryOf(TestCase):
    """
    Tests for the :class:`Registry` implementation returned by the
    :meth:`Registry.of` factory method.
    """

    def setUp(self) -> None:
        super().setUp()
        self._instance: Registry = Registry.of()
        self._instance["ITEM_KEY_1"] = "ITEM_VALUE_1"
        self._instance["ITEM_KEY_2"] = "ITEM_VALUE_2"

    def test_contains_magic_method_return_value(self) -> None:
        """
        :meth:`Registry.__contain__` should return ``True`` if an item with the
        specified key exists in the registry or ``False`` otherwise.
        """

        assert "ITEM_KEY_1" in self._instance
        assert "ITEM_KEY_2" in self._instance
        assert "ITEM_KEY_3" not in self._instance

    def test_delitem_magic_method_side_effects_on_existing_value(self) -> None:
        """
        :meth:`Registry.__delitem__` should remove the given item from the
        registry if it is already present.
        """

        output: set[str] = set()

        @connect(RegistryItemRemoved, dispatcher=self._instance.dispatcher)
        def on_reg_item_removed(signal: RegistryItemRemoved) -> None:  # pyright: ignore
            output.add(signal.item_key)

        del self._instance["ITEM_KEY_1"]
        del self._instance["ITEM_KEY_2"]

        assert "ITEM_KEY_1" in output
        assert "ITEM_KEY_2" in output
        assert "ITEM_KEY_1" not in self._instance
        assert "ITEM_KEY_2" not in self._instance

    def test_delitem_magic_method_fails_on_missing_item(self) -> None:
        """
        :meth:`Registry.__delitem__` should raise a
        :exc:`NoSuchRegistryItemError` when given an item that is non-existent
        in the registry.
        """

        with pytest.raises(NoSuchRegistryItemError) as exc_info:
            del self._instance["ITEM_KEY_3"]

        assert exc_info.value.item_key == "ITEM_KEY_3"

    def test_delitem_magic_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`Registry.__delitem__` should raise a :exc:`ValueError` when
        given a ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            del self._instance[item_key]

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_getitem_magic_method_return_value_on_existing_value(self) -> None:
        """
        :meth:`Registry.__getitem__` should return the value associated with
        the given item from the registry if it is already present.
        """

        assert self._instance["ITEM_KEY_1"] == "ITEM_VALUE_1"
        assert self._instance["ITEM_KEY_2"] == "ITEM_VALUE_2"

    def test_getitem_magic_method_fails_on_missing_item(self) -> None:
        """
        :meth:`Registry.__getitem__` should raise a
        :exc:`NoSuchRegistryItemError` when given a key of a non-existent item
        in the registry.
        """

        with pytest.raises(NoSuchRegistryItemError) as exc_info:
            value = self._instance["ITEM_KEY_3"]  # pyright: ignore  # noqa: F841

        assert exc_info.value.item_key == "ITEM_KEY_3"

    def test_getitem_magic_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`Registry.__getitem__` should raise a :exc:`ValueError` when
        given a ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            value = self._instance[item_key]  # pyright: ignore  # noqa: F841

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_setitem_magic_method_side_effects(self) -> None:
        """
        :meth:`Registry.__setitem__` should add an item in the registry or
        update the value of an existing item.
        """

        output: dict[str, str] = {}

        @connect(RegistryItemSet, dispatcher=self._instance.dispatcher)
        def on_reg_item_set(signal: RegistryItemSet) -> None:  # pyright: ignore
            output[signal.item_key] = signal.item_value

        # Update existing item
        self._instance["ITEM_KEY_1"] = "IV_1"
        self._instance["ITEM_KEY_2"] = "IV_2"
        # Set item
        self._instance["ITEM_KEY_3"] = "IV_3"

        assert self._instance["ITEM_KEY_1"] == output["ITEM_KEY_1"] == "IV_1"
        assert self._instance["ITEM_KEY_2"] == output["ITEM_KEY_2"] == "IV_2"
        assert self._instance["ITEM_KEY_3"] == output["ITEM_KEY_3"] == "IV_3"

    def test_setitem_magic_method_fails_on_non_item_key(self) -> None:
        """
        :meth:`Registry.__setitem__` should raise a :exc:`ValueError` when
        given a ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            self._instance[item_key] = "ITEM_VALUE"

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_get_method_return_value(self) -> None:
        """
        :meth:`Registry.get` should return the value associated with the given
        item from the registry if it is already present. It should return
        ``None`` of the given default if the item is not in the registry.
        """

        assert self._instance.get("ITEM_KEY_1") == "ITEM_VALUE_1"
        assert self._instance.get("ITEM_KEY_2") == "ITEM_VALUE_2"
        assert self._instance.get("ITEM_KEY_3") is None
        assert self._instance.get("ITEM_KEY_3", default="IV_3") == "IV_3"

    def test_get_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`Registry.get` should raise a :exc:`ValueError` when given a
        ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            value = self._instance.get(item_key)  # pyright: ignore  # noqa: F841

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_pop_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`Registry.pop` should raise a :exc:`ValueError` when given a
        ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            value = self._instance.pop(item_key)  # pyright: ignore  # noqa: F841

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_pop_method_side_effects(self) -> None:
        """
        :meth:`Registry.pop` should remove and return the given item from the
        registry if it is already present. If not, it should return ``None`` or
        the given default.
        """

        output: set[str] = set()

        @connect(RegistryItemRemoved, dispatcher=self._instance.dispatcher)
        def on_reg_item_removed(signal: RegistryItemRemoved) -> None:  # pyright: ignore
            output.add(signal.item_key)

        assert self._instance.pop("ITEM_KEY_1") == "ITEM_VALUE_1"
        assert self._instance.pop("ITEM_KEY_2") == "ITEM_VALUE_2"
        assert self._instance.pop("ITEM_KEY_3") is None
        assert self._instance.pop("ITEM_KEY_4", default="IV_4") == "IV_4"
        assert "ITEM_KEY_1" in output
        assert "ITEM_KEY_2" in output
        assert "ITEM_KEY_3" not in output
        assert "ITEM_KEY_4" not in output
        assert "ITEM_KEY_1" not in self._instance
        assert "ITEM_KEY_2" not in self._instance

    def test_setdefault_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`Registry.setdefault` should raise a :exc:`ValueError` when given
        a ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            self._instance.setdefault(item_key, "VALUE")

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_setdefault_method_side_effects(self) -> None:
        """
        :meth:`Registry.setdefault` should retrieve the value associated with
        the specified key from the registry, or set it if the key does not
        exist.
        """

        output: dict[str, str] = {}

        @connect(RegistryItemSet, dispatcher=self._instance.dispatcher)
        def on_reg_item_set(signal: RegistryItemSet) -> None:  # pyright: ignore
            output[signal.item_key] = signal.item_value

        # Retrieve existing item
        assert self._instance.setdefault("ITEM_KEY_1", "IV1") == "ITEM_VALUE_1"
        assert self._instance.setdefault("ITEM_KEY_2", "IV2") == "ITEM_VALUE_2"
        # Set item
        assert self._instance.setdefault("ITEM_KEY_3", "IV3") == "IV3"

        assert "ITEM_KEY_1" not in output
        assert "ITEM_KEY_2" not in output
        assert self._instance["ITEM_KEY_3"] == output["ITEM_KEY_3"] == "IV3"


class TestRegistryProxy(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self._source_registry: Registry = Registry.of()
        self._instance: RegistryProxy = RegistryProxy(self._source_registry)
        self._instance["ITEM_KEY_1"] = "ITEM_VALUE_1"
        self._instance["ITEM_KEY_2"] = "ITEM_VALUE_2"

    def test_init_fails_when_source_registry_is_not_a_registry(self) -> None:
        """
        :meth:`RegistryProxy.__init__` should raise a :exc:`TypeError` when
        the ``source_registry`` parameter given is not an instance of
        :class:`Registry`.
        """
        with pytest.raises(TypeError, match="is not an instance of"):
            RegistryProxy(source_registry=None)   # type: ignore

        with pytest.raises(TypeError, match="is not an instance of"):
            RegistryProxy(source_registry={})  # type: ignore

    def test_contains_magic_method_return_value(self) -> None:
        """
        :meth:`RegistryProxy.__contain__` should return ``True`` if an item
        with the specified key exists in the registry or ``False`` otherwise.
        """

        assert "ITEM_KEY_1" in self._instance
        assert "ITEM_KEY_2" in self._instance
        assert "ITEM_KEY_3" not in self._instance

    def test_delitem_magic_method_side_effects_on_existing_value(self) -> None:
        """
        :meth:`RegistryProxy.__delitem__` should remove the given item from the
        registry if it is already present.
        """

        output: set[str] = set()

        @connect(RegistryItemRemoved, dispatcher=self._instance.dispatcher)
        def on_reg_item_removed(signal: RegistryItemRemoved) -> None:  # pyright: ignore
            output.add(signal.item_key)

        del self._instance["ITEM_KEY_1"]
        del self._instance["ITEM_KEY_2"]

        assert "ITEM_KEY_1" in output
        assert "ITEM_KEY_2" in output
        assert "ITEM_KEY_1" not in self._instance
        assert "ITEM_KEY_2" not in self._instance

    def test_delitem_magic_method_fails_on_missing_item(self) -> None:
        """
        :meth:`RegistryProxy.__delitem__` should raise a
        :exc:`NoSuchRegistryItemError` when given an item that is non-existent
        in the registry.
        """

        with pytest.raises(NoSuchRegistryItemError) as exc_info:
            del self._instance["ITEM_KEY_3"]

        assert exc_info.value.item_key == "ITEM_KEY_3"

    def test_delitem_magic_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`RegistryProxy.__delitem__` should raise a :exc:`ValueError` when
        given a ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            del self._instance[item_key]

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_getitem_magic_method_return_value_on_existing_value(self) -> None:
        """
        :meth:`RegistryProxy.__getitem__` should return the value associated
        with the given item from the registry if it is already present.
        """

        assert self._instance["ITEM_KEY_1"] == "ITEM_VALUE_1"
        assert self._instance["ITEM_KEY_2"] == "ITEM_VALUE_2"

    def test_getitem_magic_method_fails_on_missing_item(self) -> None:
        """
        :meth:`RegistryProxy.__getitem__` should raise a
        :exc:`NoSuchRegistryItemError` when given a key of a non-existent item
        in the registry.
        """

        with pytest.raises(NoSuchRegistryItemError) as exc_info:
            value = self._instance["ITEM_KEY_3"]  # pyright: ignore  # noqa: F841

        assert exc_info.value.item_key == "ITEM_KEY_3"

    def test_getitem_magic_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`RegistryProxy.__getitem__` should raise a :exc:`ValueError` when
        given a ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            value = self._instance[item_key]  # pyright: ignore  # noqa: F841

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_setitem_magic_method_side_effects(self) -> None:
        """
        :meth:`RegistryProxy.__setitem__` should add an item in the registry or
        update the value of an existing item.
        """

        output: dict[str, str] = {}

        @connect(RegistryItemSet, dispatcher=self._instance.dispatcher)
        def on_reg_item_set(signal: RegistryItemSet) -> None:  # pyright: ignore
            output[signal.item_key] = signal.item_value

        # Update existing item
        self._instance["ITEM_KEY_1"] = "IV_1"
        self._instance["ITEM_KEY_2"] = "IV_2"
        # Set item
        self._instance["ITEM_KEY_3"] = "IV_3"

        assert self._instance["ITEM_KEY_1"] == output["ITEM_KEY_1"] == "IV_1"
        assert self._instance["ITEM_KEY_2"] == output["ITEM_KEY_2"] == "IV_2"
        assert self._instance["ITEM_KEY_3"] == output["ITEM_KEY_3"] == "IV_3"

    def test_setitem_magic_method_fails_on_non_item_key(self) -> None:
        """
        :meth:`RegistryProxy.__setitem__` should raise a :exc:`ValueError` when
        given a ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            self._instance[item_key] = "ITEM_VALUE"

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_get_method_return_value(self) -> None:
        """
        :meth:`RegistryProxy.get` should return the value associated with the
        given item from the registry if it is already present. It should return
        ``None`` of the given default if the item is not in the registry.
        """

        assert self._instance.get("ITEM_KEY_1") == "ITEM_VALUE_1"
        assert self._instance.get("ITEM_KEY_2") == "ITEM_VALUE_2"
        assert self._instance.get("ITEM_KEY_3") is None
        assert self._instance.get("ITEM_KEY_3", default="IV_3") == "IV_3"

    def test_get_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`RegistryProxy.get` should raise a :exc:`ValueError` when given
        a ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            value = self._instance.get(item_key)  # pyright: ignore  # noqa: F841

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_pop_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`RegistryProxy.pop` should raise a :exc:`ValueError` when given a
        ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            value = self._instance.pop(item_key)  # pyright: ignore  # noqa: F841

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_pop_method_side_effects(self) -> None:
        """
        :meth:`RegistryProxy.pop` should remove and return the given item from
        the registry if it is already present. If not, it should return
        ``None`` or the given default.
        """

        output: set[str] = set()

        @connect(RegistryItemRemoved, dispatcher=self._instance.dispatcher)
        def on_reg_item_removed(signal: RegistryItemRemoved) -> None:  # pyright: ignore
            output.add(signal.item_key)

        assert self._instance.pop("ITEM_KEY_1") == "ITEM_VALUE_1"
        assert self._instance.pop("ITEM_KEY_2") == "ITEM_VALUE_2"
        assert self._instance.pop("ITEM_KEY_3") is None
        assert self._instance.pop("ITEM_KEY_4", default="IV_4") == "IV_4"
        assert "ITEM_KEY_1" in output
        assert "ITEM_KEY_2" in output
        assert "ITEM_KEY_3" not in output
        assert "ITEM_KEY_4" not in output
        assert "ITEM_KEY_1" not in self._instance
        assert "ITEM_KEY_2" not in self._instance

    def test_set_source_fails_when_source_register_is_not_a_registry(self) -> None:  # noqa: E501
        """
        :meth:`RegistryProxy.set_source` should raise a :exc:`TypeError` when
        the ``source_registry`` parameter given is not an instance of
        :class:`Registry`.
        """

        with pytest.raises(TypeError, match="is not an instance of"):
            self._instance.set_source(source_registry=None)  # type: ignore

    def test_setdefault_method_fails_on_none_item_key(self) -> None:
        """
        :meth:`RegistryProxy.setdefault` should raise a :exc:`ValueError` when
        given a ``None`` item key.
        """

        item_key: str = None  # type: ignore

        with pytest.raises(ValueError, match="MUST not be None.") as exc_info:
            self._instance.setdefault(item_key, "VALUE")

        assert exc_info.value.args[0] == "'key' MUST not be None."

    def test_setdefault_method_side_effects(self) -> None:
        """
        :meth:`RegistryProxy.setdefault` should retrieve the value associated
        with the specified key from the registry, or set it if the key does not
        exist.
        """

        output: dict[str, str] = {}

        @connect(RegistryItemSet, dispatcher=self._instance.dispatcher)
        def on_reg_item_set(signal: RegistryItemSet) -> None:  # pyright: ignore
            output[signal.item_key] = signal.item_value

        # Retrieve existing item
        assert self._instance.setdefault("ITEM_KEY_1", "IV1") == "ITEM_VALUE_1"
        assert self._instance.setdefault("ITEM_KEY_2", "IV2") == "ITEM_VALUE_2"
        # Set item
        assert self._instance.setdefault("ITEM_KEY_3", "IV3") == "IV3"

        assert "ITEM_KEY_1" not in output
        assert "ITEM_KEY_2" not in output
        assert self._instance["ITEM_KEY_3"] == output["ITEM_KEY_3"] == "IV3"
