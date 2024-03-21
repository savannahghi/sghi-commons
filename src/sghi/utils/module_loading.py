"""Utilities to load modules, types, and objects from dotted path strings."""

import inspect
from typing import Any, Final, TypeVar, cast

from importlib_metadata import EntryPoint

from .checkers import ensure_not_none, ensure_not_none_nor_empty
from .others import type_fqn

# =============================================================================
# TYPES
# =============================================================================


_T = TypeVar("_T")


# =============================================================================
# CONSTANTS
# =============================================================================


_UNKNOWN_STR: Final[str] = "UNKNOWN"


# =============================================================================
# IMPORT UTILITIES
# =============================================================================


def import_string(dotted_path: str) -> Any:  # noqa: ANN401
    """Import a dotted module path and return the Python object designated by
    the last name in the path.

    The `dotted path` can refer to any "importable" Python object
    including modules. It should also conform to the format defined by the
    Python packaging conventions. See :doc:`the packaging docs on entry points
    <pypackage:specifications/entry-points>` for more information.

    Raise :exc:`ImportError` if the import failed.

    :param dotted_path: A dotted path to a Python object. This MUST not be
        ``None`` or empty.

    :return: The Python object designated by the last name in the path.

    :raises ImportError: If the import fails for some reason.
    :raises ValueError: If the given dotted path is ``None`` or empty.
    """
    entry_point = EntryPoint(
        name=_UNKNOWN_STR,
        group=_UNKNOWN_STR,
        value=ensure_not_none_nor_empty(
            dotted_path,
            "'dotted_path' MUST not be None or empty.",
        ),
    )
    try:
        return entry_point.load()
    except AttributeError as exp:
        _err_msg: str = str(exp)
        raise ImportError(_err_msg) from exp


def import_string_as_klass(
    dotted_path: str,
    target_klass: type[_T],
) -> type[_T]:
    """Import a dotted module path as the given type.

    Raise :exc:`ImportError` if the import failed or a :exc:`TypeError` if the
    imported Python object is not of the given type or derived from it.

    :param dotted_path: A dotted path to a class. This MUST not be ``None`` or
        empty.
    :param target_klass: The type that the imported module should have or be
        derived from. This MUST not be ``None``.

    :return: The class designated by the last name in the path.

    :raises ImportError: If the import fails for some reason.
    :raises TypeError: If the imported object is not of the given type or
        derived from it.
    :raises ValueError: If ``dotted_path`` is either ``None`` or empty or
        ``target_klass`` is ``None``.
    """
    ensure_not_none(target_klass, "'target_klass' MUST not be None.")
    _module = import_string(dotted_path)
    if not inspect.isclass(_module) or not issubclass(_module, target_klass):
        err_msg: str = (
            f"Invalid value, '{dotted_path}' does not refer to a valid type "
            f"or to a subtype of '{type_fqn(target_klass)}'."
        )
        raise TypeError(err_msg)

    return cast(type[target_klass], _module)
