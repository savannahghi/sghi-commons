"""
Useful typings for use with type annotations as defined by
:doc:`PEP 484<peps:pep-0484>` and other subsequent related PEPs.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from typing_extensions import Self

# =============================================================================
# TYPES
# =============================================================================


_CT_contra = TypeVar("_CT_contra", bound="Comparable", contravariant=True)


# =============================================================================
# TYPINGS
# =============================================================================


@runtime_checkable
class Comparable(Protocol[_CT_contra]):
    """Protocol defining an object that supports rich comparisons.

    A valid ``Comparable`` object MUST implement (at-least) the following
    comparison methods:

    - :meth:`__eq__`
    - :meth:`__le__`
    - :meth:`__lt__`

    .. seealso::

        The official Python
        :doc:`Comparisons docs <python:reference/expressions>`.

    .. automethod:: __eq__
    .. automethod:: __ge__
    .. automethod:: __gt__
    .. automethod:: __le__
    .. automethod:: __lt__
    .. automethod:: __ne__
    """

    __slots__ = ()

    @abstractmethod
    def __eq__(self: Self, other: object, /) -> bool:
        """Same as ``self == other``.

        :param other: The other object to compare for equality with this one.

        :return: ``True`` if ``self == other``, ``False`` otherwise.
        """
        ...

    def __ge__(self: Self, other: _CT_contra, /) -> bool:
        """Same as ``self >= other``.

        :param other: The other object to compare for equality with this one.

        :return: ``True`` if ``self >= other``, ``False`` otherwise.
        """
        return not self < other

    def __gt__(self: Self, other: _CT_contra, /) -> bool:
        """Same as ``self > other``.

        :param other: The other object to compare for equality with this one.

        :return: ``True`` if ``self > other``, ``False`` otherwise.
        """
        return not(self < other or self == other)

    @abstractmethod
    def __le__(self: Self, other: _CT_contra, /) -> bool:
        """Same as ``self <= other``.

        :param other: The other object to compare to this one.

        :return: ``True`` if ``self <= other``, ``False`` otherwise.
        """
        ...

    @abstractmethod
    def __lt__(self: Self, other: _CT_contra, /) -> bool:
        """Same as ``self < other``.

        :param other: The other object to compare to this one.

        :return: ``True`` if ``self < other``, ``False`` otherwise.
        """
        ...

    def __ne__(self: Self, other: object, /) -> bool:
        """Same as ``self != other``.

        :param other: The other object to compare for equality with this one.

        :return: ``True`` if ``self != other``, ``False`` otherwise.
        """
        return not self == other


# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = [
    "Comparable",
]
