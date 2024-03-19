from collections.abc import Iterable, Mapping, Sequence
from numbers import Number
from typing import Any, Protocol

import pytest

from sghi.disposable import Disposable
from sghi.typing import Comparable
from sghi.utils import import_string, import_string_as_klass, type_fqn


def test_import_string_returns_imported_object_on_valid_input() -> None:
    """
    :func:`import_string` should return the imported Python object when given a
    valid dotted path string.
    """
    assert import_string("pytest") is pytest
    assert import_string("sghi.utils:import_string") is import_string
    assert import_string("sghi.utils.others:type_fqn") is type_fqn
    assert (
        type_fqn(import_string("importlib.metadata:EntryPoint"))
        == "importlib.metadata.EntryPoint"
    )


def test_import_string_fails_on_invalid_input() -> None:
    """
    :func:`import_string` should raise an ``ImportError`` when given an invalid
    dotted path string.
    """
    invalid_dotted_paths: Iterable[str] = (
        "pytestt",
        "sghi.utils.import_string",  # 'import_string' is not a module
        "sghi.utils:import",  # 'import' does not exist
        "django.contrib",  # Not installed. Hopefully, 🤞.
    )
    for dotted_path in invalid_dotted_paths:
        with pytest.raises(ImportError):
            import_string(dotted_path)


def test_import_string_fails_on_none_or_empty_input() -> None:
    """
    :func:`import_string` should raise a ``ValueError`` when given a ``None``
    or empty dotted string.
    """
    dot_path: str = None  # type: ignore
    invalid_dotted_paths: Iterable[str] = (
        "",
        dot_path,
    )
    for dotted_path in invalid_dotted_paths:
        with pytest.raises(ValueError, match="MUST not be None or empty."):
            import_string(dotted_path)


def test_import_string_as_klass_returns_imported_object_on_valid_input() -> (
    None
):
    """
    :func:`import_string_as_klass` should return the imported type when given a
    valid dotted path string.
    """
    isak = import_string_as_klass

    assert isak("builtins:dict", Mapping) is dict
    assert isak("sghi.disposable:Disposable", Disposable) is Disposable
    assert isak("sghi.typing:Comparable", Protocol) is Comparable  # pyright: ignore[reportArgumentType]


def test_import_string_as_klass_fails_on_invalid_dotted_path() -> None:
    """
    :func:`import_import_string_as_klass` should raise an ``ImportError`` when
    given an invalid dotted path string.
    """
    invalid_dotted_paths: Iterable[str] = (
        "pytestt",
        "sghi.typing:Compare",  # 'Compare' does not exist
        "sghi.utils:Import",  # 'Import' does not exist
        "django.models:Model",  # Not installed. Hopefully, 🤞.
    )
    for dotted_path in invalid_dotted_paths:
        with pytest.raises(ImportError):
            import_string_as_klass(dotted_path, type)


def test_import_string_as_klass_fails_on_none_inputs() -> None:
    """
    :func:`import_import_string_as_klass` should raise a ``Value`` when
    either the dotted path string or target type is ``None``.
    """
    with pytest.raises(ValueError, match="MUST not be None"):
        import_string_as_klass(None, Mapping)  # type: ignore

    with pytest.raises(ValueError, match="MUST not be None"):
        import_string_as_klass("sghi.typing:Comparable", None)  # type: ignore


def test_import_string_as_klass_fails_on_wrong_dotted_path_type() -> None:
    """
    :func:`import_import_string_as_klass` should raise a ``TypeError`` when
    given an invalid dotted path string that doesn't refer to an object of the
    given type.
    """
    wrong_inputs: Iterable[tuple[str, type[Any]]] = (
        ("builtins:dict", Sequence),
        ("sghi.disposable:Disposable", Mapping),
        ("sghi.typing:Comparable", Number),
    )
    for dotted_path, klass in wrong_inputs:
        with pytest.raises(TypeError, match="does not refer to a valid type"):
            import_string_as_klass(dotted_path, klass)
