from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import TestCase

from sghi.typing import Comparable
from sghi.utils.checkers import ensure_not_none

if TYPE_CHECKING:
    from typing import Self

# =============================================================================
# COMPARABLE TEST IMPLEMENTATIONS
# =============================================================================


class _SimpleComparable(Comparable["_SimpleComparable"]):
    __slots__ = ("_value",)

    def __init__(self, value: int) -> None:
        super().__init__()
        self._value: int = ensure_not_none(value)

    def __eq__(self: Self, other: object, /) -> bool:
        if not isinstance(other, _SimpleComparable):
            return False
        return self._value == other._value

    def __le__(self: Self, other: _SimpleComparable, /) -> bool:
        return self._value.__le__(ensure_not_none(other)._value)

    def __lt__(self: Self, other: _SimpleComparable, /) -> bool:
        return self._value.__lt__(ensure_not_none(other)._value)

    @classmethod
    def of(cls, value: int) -> Self:
        return cls(value)


# =============================================================================
# TESTS
# =============================================================================


class TestComparable(TestCase):
    """Tests for the ``Comparable`` protocol class."""

    def setUp(self) -> None:
        super().setUp()
        self._four: Comparable = _SimpleComparable.of(4)
        self._five: Comparable = _SimpleComparable.of(5)
        self._six1: Comparable = _SimpleComparable.of(6)
        self._six2: Comparable = _SimpleComparable.of(6)

    def test_greater_or_equal_return_value(self) -> None:
        """The return value of the default implementation of
        :meth:`Comparable.__ge__` should return ``True`` when ``a >= b``.
        """
        assert self._five >= self._four
        assert self._six1 >= self._six2
        assert self._six1 >= self._four
        assert self._six2 >= self._five
        assert not self._four >= self._five
        assert not self._four >= self._six1
        assert not self._five >= self._six1

    def test_greater_than_return_value(self) -> None:
        """The return value of the default implementation of
        :meth:`Comparable.__gt__` should return ``True`` when ``a > b``.
        """
        assert self._five > self._four
        assert self._six1 > self._four
        assert self._six2 > self._five
        assert not self._four > self._five
        assert not self._four > self._six1
        assert not self._five > self._six1
        assert not self._six1 > self._six2

    def test_not_equal_return_value(self) -> None:
        """The return value of the default implementation of
        :meth:`Comparable.__ne__` should return ``True`` when ``a != b``.
        """
        assert self._five != self._four
        assert self._four != self._six1
        assert not self._six1.__ne__(self._six1)
        assert not self._six1.__ne__(self._six2)
