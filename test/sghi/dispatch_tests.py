import gc
from dataclasses import dataclass, field
from unittest import TestCase

import pytest

from sghi.dispatch import Dispatcher, DispatcherProxy, Signal, connect
from sghi.utils import ensure_greater_or_equal, type_fqn

# =============================================================================
# TESTS HELPERS
# =============================================================================


@dataclass(frozen=True, slots=True, match_args=True)
class CounterAdvanced(Signal):
    current_value: int = field()
    advanced_by: int = field()


@dataclass(frozen=True, slots=True, match_args=True)
class CounterExhausted(Signal):
    max_count: int = field()


@dataclass(frozen=True, slots=True, match_args=True)
class CounterReset(Signal):
    current_value: int = field()


class Counter:

    __slots__ = ("_current", "_max_count", "_dispatcher")

    def __init__(self, max_count: int) -> None:
        super().__init__()
        ensure_greater_or_equal(max_count, 0)
        self._max_count: int = max_count
        self._current: int = 0
        self._dispatcher: Dispatcher = Dispatcher.of()

    def advance_counter(self, by: int = 1) -> int:
        ensure_greater_or_equal(by, 1, "MUST advance by at least 1.")
        if self._current >= self._max_count:
            self._dispatcher.send(CounterExhausted(self._max_count))
            return self._current

        self._current += by
        self._dispatcher.send(CounterAdvanced(self._current, by))
        return self._current

    def reset(self) -> None:
        self._current = 0
        self._dispatcher.send(CounterReset(self._current))

    @property
    def current_value(self) -> int:
        return self._current

    @property
    def dispatcher(self) -> Dispatcher:
        return self._dispatcher

    @property
    def max_count(self) -> int:
        return self._max_count


# =============================================================================
# TESTS
# =============================================================================


class TestDispatcher(TestCase):
    """
    Tests for the :class:`Dispatcher` interface default implementations.
    """

    def test_of_factory_method_return_value(self) -> None:
        """:meth:`Dispatcher.of` should return a ``Dispatch`` instance."""

        assert isinstance(Dispatcher.of(), Dispatcher)

    def test_of_proxy_factory_method_return_value(self) -> None:
        """
        :meth:`Dispatcher.of_proxy` should return a ``DispatcherProxy``
        instance.
        """

        assert isinstance(Dispatcher.of_proxy(), DispatcherProxy)


class TestDispatcherOf(TestCase):
    """
    Tests for the :class:`Dispatcher` implementation returned by the
    :meth:`Dispatcher.of` factory method.
    """

    def setUp(self) -> None:
        super().setUp()
        self._instance: Dispatcher = Dispatcher.of()
        self._counter_max_value: int = 10
        self._counter: Counter = Counter(self._counter_max_value)

    def test_connect_fails_on_non_type_signal_type_as_input(self) -> None:
        """
        :meth:`Dispatcher.connect` should raise a :exc:`TypeError` when
        given a `signal_type` parameter that is not a type.
        """
        with pytest.raises(TypeError, match="MUST be a type") as exc_info:
            self._instance.connect(
                signal_type=CounterReset(0),  # type: ignore # not a type
                receiver=self.on_counter_reset,
            )

        assert exc_info.value.args[0] == "'signal_type' MUST be a type."

    def test_connect_fails_on_signal_type_not_signal_subclass(self) -> None:
        """
        :meth:`Dispatcher.connect` should raise a :exc:`TypeError` when
        given a `signal_type` parameter that is not a subclass of
        :class:`Signal`.
        """
        with pytest.raises(TypeError, match="MUST be a subclass") as exc_info:
            self._instance.connect(
                signal_type=str,  # type: ignore # not a type
                receiver=self.on_counter_reset,
            )

        assert exc_info.value.args[0] == (
                f"'signal_type' MUST be a subclass of '{type_fqn(Signal)}'."
        )

    def test_connect_fails_on_none_receiver_as_input_value(self) -> None:
        """
        :meth:`Dispatcher.connect` should raise a :exc:`ValueError` when given
        a ``None`` value on the ``receiver`` parameter.
        """
        with pytest.raises(ValueError, match="MUST not be None"):
            self._instance.connect(CounterAdvanced, None)  # type: ignore

    def test_connect_side_effects_when_weak_is_set_to_false(self) -> None:
        """
        :meth:`Dispatcher.connect` should add a receiver and retain it even
        when it would normally be garbage collected when the ``weak``
        parameter is set to ``False``.
        """
        output: list[int] = []

        def on_counter_advanced(signa: CounterAdvanced) -> None:
            output.append(signa.current_value)

        class OnCounterAdvance:
            def execute(self, signal: CounterAdvanced) -> None:
                output.append(signal.current_value)

        self._counter.dispatcher.connect(
            CounterAdvanced,
            on_counter_advanced,
            weak=False,
        )
        self._counter.dispatcher.connect(
            CounterAdvanced,
            OnCounterAdvance().execute,
            weak=False,
        )

        del on_counter_advanced
        gc.collect()

        self._counter.advance_counter()

        assert len(output) == 2
        assert output[0] == 1
        assert output[1] == 1

    def test_connect_side_effects_when_weak_is_set_to_true(self) -> None:
        """
        :meth:`Dispatcher.connect` should add a receiver but automatically
        remove it after garbage collection when the ``weak`` parameter is set
        to ``True``.
        """
        output: list[int] = []

        def on_counter_advanced(signa: CounterAdvanced) -> None:
            output.append(signa.current_value)

        class OnCounterAdvance:
            def execute(self, signal: CounterAdvanced) -> None:
                output.append(signal.current_value)

        self._counter.dispatcher.connect(
            CounterAdvanced,
            on_counter_advanced,
            weak=True,
        )
        self._counter.dispatcher.connect(
            CounterAdvanced,
            OnCounterAdvance().execute,
            weak=True,
        )

        del on_counter_advanced
        gc.collect()

        self._counter.advance_counter()

        assert len(output) == 0

    def test_disconnect_fails_on_non_type_signal_type_as_input(self) -> None:
        """
        :meth:`Dispatcher.disconnect` should raise a :exc:`TypeError` when
        given a `signal_type` parameter that is not a type.
        """
        with pytest.raises(TypeError, match="MUST be a type") as exc_info:
            self._instance.disconnect(
                signal_type=CounterReset(0),  # type: ignore # not a type
                receiver=self.on_counter_reset,
            )

        assert exc_info.value.args[0] == "'signal_type' MUST be a type."

    def test_disconnect_fails_on_signal_type_not_signal_subclass(self) -> None:
        """
        :meth:`Dispatcher.disconnect` should raise a :exc:`TypeError` when
        given a `signal_type` parameter that is not a subclass of
        :class:`Signal`.
        """
        with pytest.raises(TypeError, match="MUST be a subclass") as exc_info:
            self._instance.disconnect(
                signal_type=str,  # type: ignore # not a type
                receiver=self.on_counter_reset,
            )

        assert exc_info.value.args[0] == (
            f"'signal_type' MUST be a subclass of '{type_fqn(Signal)}'."
        )

    def test_disconnect_fails_on_none_receiver_as_input_value(self) -> None:
        """
        :meth:`Dispatcher.disconnect` should raise a :exc:`ValueError` when
        given a ``None`` value on the ``receiver`` parameter.
        """
        with pytest.raises(ValueError, match="MUST not be None"):
            self._instance.disconnect(CounterAdvanced, None)  # type: ignore

    def test_disconnect_side_effects_when_weak_is_set_to_false(self) -> None:
        """
        :meth:`Dispatcher.disconnect` should remove a connected receiver even
        when it was not connected weakly.
        """
        counter: Counter = self._counter
        output: list[int] = []

        @connect(CounterAdvanced, dispatcher=counter.dispatcher, weak=False)
        def on_counter_advanced1(signa: CounterAdvanced) -> None:  # type: ignore
            output.append(signa.current_value)

        @connect(CounterAdvanced, dispatcher=counter.dispatcher, weak=False)
        def on_counter_advanced2(signa: CounterAdvanced) -> None:
            output.append(signa.current_value)

        counter.advance_counter()
        counter.dispatcher.disconnect(CounterAdvanced, on_counter_advanced2)
        counter.advance_counter()  # Should result in 2 being added to output

        assert len(output) == 3
        assert output[0] == 1
        assert output[1] == 1
        assert output[2] == 2

    def test_disconnect_side_effects_when_weak_is_set_to_true(self) -> None:
        """
        :meth:`Dispatcher.disconnect` should remove a connected receiver even
        when it was connected weakly.
        """
        counter: Counter = self._counter
        output: list[int] = []

        @connect(CounterAdvanced, dispatcher=counter.dispatcher, weak=True)
        def on_counter_advanced1(signa: CounterAdvanced) -> None:
            output.append(signa.current_value)

        @connect(CounterAdvanced, dispatcher=counter.dispatcher, weak=True)
        def on_counter_advanced2(signa: CounterAdvanced) -> None:  # type: ignore
            output.append(signa.current_value)

        counter.advance_counter()
        counter.dispatcher.disconnect(CounterAdvanced, on_counter_advanced1)
        counter.advance_counter()  # Should result in 2 being added to output

        assert len(output) == 3
        assert output[0] == 1
        assert output[1] == 1
        assert output[2] == 2

    def test_send_fails_when_signal_is_not_a_signal(self) -> None:
        """
        :method:`Dispatcher.send` should raise a :exc:`ValueError` when the
        ``signal`` parameter is not an instance of :class:`Signal`.
        """

    def test_send_side_effects_when_robust_is_set_to_false(self) -> None:
        """
        :meth:`Dispatcher.send` should propagate any errors raised by
        receivers.
        """
        @connect(CounterReset, dispatcher=self._instance, weak=False)
        def on_counter_reset(signal: CounterReset) -> None:  # type: ignore
            raise ZeroDivisionError

        with pytest.raises(ZeroDivisionError):
            self._instance.send(CounterReset(0), robust=False)

    def test_send_side_effects_when_robust_is_set_to_true(self) -> None:
        """
        :meth:`Dispatcher.send` should silently discard any errors raised by
        receivers.
        """
        output: list[int] = []

        @connect(CounterReset, dispatcher=self._instance, weak=False)
        def on_counter_reset1(signal: CounterReset) -> None:  # type: ignore
            raise ZeroDivisionError

        @connect(CounterReset, dispatcher=self._instance, weak=False)
        def on_counter_reset2(signal: CounterReset) -> None:  # type: ignore
            output.append(signal.current_value)

        try:
            self._instance.send(CounterReset(0), robust=True)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"'send' raised an unexpected error: '{exc}'.")

        assert len(output) == 1
        assert output[0] == 0

    @staticmethod
    def on_counter_reset(signal: CounterReset) -> None:
        ...


class TestDispatcherProxy(TestCase):
    """Tests for the :class:`DispatcherProxy` class."""

    def setUp(self) -> None:
        super().setUp()
        self._source_dispatcher: Dispatcher = Dispatcher.of()
        self._instance: DispatcherProxy = DispatcherProxy(
            self._source_dispatcher,
        )

    def test_init_fails_when_source_dispatcher_is_not_a_dispatcher(self) -> None:  # noqa: E501
        """
        :meth:`DispatcherProxy.__init__` should raise a :exc:`TypeError` when
        the ``source_dispatcher`` parameter given is not an instance of
        :class:`Dispatcher`.
        """
        with pytest.raises(TypeError, match="is not an instance of"):
            DispatcherProxy(source_dispatcher=None)  # type: ignore

        with pytest.raises(TypeError, match="is not an instance of"):
            DispatcherProxy(source_dispatcher={})  # type: ignore

    def test_connect_side_effects(self) -> None:
        """
        :meth:`DispatcherProxy.connect` should have similar side effects to the
        wrapped `Dispatcher` instance.
        """
        output: list[int] = []

        def on_counter_advanced(signa: CounterAdvanced) -> None:
            output.append(signa.current_value)

        class OnCounterAdvance:
            def execute(self, signal: CounterAdvanced) -> None:
                output.append(signal.current_value)

        self._instance.connect(
            CounterAdvanced,
            on_counter_advanced,
            weak=False,
        )
        self._instance.connect(
            CounterAdvanced,
            OnCounterAdvance().execute,
            weak=True,
        )

        self._instance.send(CounterAdvanced(current_value=1, advanced_by=1))

        del on_counter_advanced
        gc.collect()

        self._instance.send(CounterAdvanced(current_value=10, advanced_by=9))

        assert len(output) == 2
        assert output[0] == 1
        assert output[1] == 10

    def test_disconnect_side_effects(self) -> None:
        """
        :meth:`DispatcherProxy.disconnect` should have similar side effects to
        the wrapped `Dispatcher` instance.
        """
        output: list[int] = []

        @connect(CounterAdvanced, dispatcher=self._instance, weak=False)
        def on_counter_advanced1(signa: CounterAdvanced) -> None:
            output.append(signa.current_value)

        @connect(CounterAdvanced, dispatcher=self._instance, weak=True)
        def on_counter_advanced2(signa: CounterAdvanced) -> None:
            output.append(signa.current_value)

        self._instance.send(CounterAdvanced(current_value=1, advanced_by=1))

        del on_counter_advanced2
        gc.collect()

        self._instance.disconnect(CounterAdvanced, on_counter_advanced1)
        self._instance.send(CounterAdvanced(current_value=10, advanced_by=9))

        assert len(output) == 2
        assert output[0] == 1
        assert output[1] == 1

    def test_set_source_fails_when_source_dispatch_is_not_a_dispatcher(self) -> None:  # noqa: E501
        """
        :meth:`DispatcherProxy.set_source` should raise a :exc:`TypeError` when
        the ``source_dispatcher`` parameter given is not an instance of
        :class:`Dispatcher`.
        """

        with pytest.raises(TypeError, match="is not an instance of"):
            self._instance.set_source(source_dispatcher=None)  # type: ignore
