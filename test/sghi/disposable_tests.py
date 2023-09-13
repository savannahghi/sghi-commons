from unittest import TestCase

import pytest

from sghi.disposable import Disposable, ResourceDisposedError, not_disposed

# =============================================================================
# DISPOSABLES TEST IMPLEMENTATIONS
# =============================================================================


class _SomeItemDisposedError(ResourceDisposedError):

    def __init__(self, msg: str = "SomeDisposableItem is already disposed"):
        super().__init__(message=msg)


class _SomeDisposableItem(Disposable):

    __slots__ = ("_is_disposed",)

    def __init__(self) -> None:
        super().__init__()
        self._is_disposed: bool = False

    @property
    def is_disposed(self) -> bool:
        return self._is_disposed

    def dispose(self) -> None:
        self._is_disposed = True

    @not_disposed
    def use_resources1(self) -> None:
        ...

    @not_disposed(exc_factory=_SomeItemDisposedError)
    def use_resources2(self) -> str:
        return "Some Results!"


# =============================================================================
# TESTS
# =============================================================================


class TestDisposable(TestCase):
    """Tests for the :class:`Disposable` mixin."""

    def test_object_is_disposed_on_context_manager_exit(self) -> None:
        """
        As per the default implementation of the :class:`Disposable` mixin ,
        a ``Disposable`` object's ``dispose()`` method should be invoked when
        exiting a context manager.
        """

        with _SomeDisposableItem() as disposable:
            # Resource should not be disposed at this time
            assert not disposable.is_disposed

        assert disposable.is_disposed


class TestNotDisposedDecorator(TestCase):
    """Tests for the :func:`not_disposed` decorator."""

    def test_decorated_methods_return_normally_when_not_disposed(self) -> None:
        """
        Methods decorated using the ``not_disposed`` decorator should return
        normally, i.e., without raising :exc:`ResourceDisposedError` if their
        bound ``Disposable`` object is yet to be disposed.
        """
        with _SomeDisposableItem() as disposable:
            # Resource should not be disposed at this time
            assert not disposable.is_disposed

            try:
                disposable.use_resources1()
                assert disposable.use_resources2() == "Some Results!"
            except ResourceDisposedError:
                pytest.fail(reason="Resource should not be disposed yet.")

        assert disposable.is_disposed

    def test_decorated_methods_raise_expected_errors_when_disposed(self) -> None:  # noqa: E501
        """
        Methods decorated using the ``not_disposed`` decorator should raise
        :exc:`ResourceDisposedError` or it's derivatives (depending on whether
        the ``exc_factory`` is provided) when invoked after their bound
        ``Disposable`` object is disposed.
        """

        disposable: _SomeDisposableItem = _SomeDisposableItem()
        disposable.dispose()

        assert disposable.is_disposed
        with pytest.raises(ResourceDisposedError) as exc_info1:
            disposable.use_resources1()

        with pytest.raises(_SomeItemDisposedError) as exc_info2:
            disposable.use_resources2()

        assert exc_info1.type is ResourceDisposedError
        assert exc_info1.value.message == "Resource already disposed."
        assert exc_info2.type is _SomeItemDisposedError
        assert exc_info2.value.message == "SomeDisposableItem is already disposed"  # noqa: E501
