from concurrent.futures import Future

import pytest

from sghi.disposable import Disposable, ResourceDisposedError, not_disposed
from sghi.utils import future_succeeded, type_fqn


def test_future_succeeded_fails_on_none_input() -> None:
    """:func:`future_succeeded` should raise a ``ValueError`` when given a
    ``None`` as it's input.
    """
    with pytest.raises(ValueError, match="MUST not be None") as exc_info:
        future_succeeded(None)  # type: ignore

    assert exc_info.value.args[0] == "'future' MUST not be None."


def test_future_succeeded_return_value_when_given_cancelled_futures() -> None:
    """:func:`future_succeeded` should return ``False`` when given a canceled
    ``Future`` as it's input.
    """
    future: Future[int] = Future()

    assert future.cancel()
    assert not future_succeeded(future)


def test_future_succeeded_return_value_when_given_failed_futures() -> None:
    """:func:`future_succeeded` should return ``False`` when given a ``Future``
    whose callee raised an exception as it's input.
    """
    future: Future[int] = Future()
    future.set_exception(ValueError(":("))

    assert future.exception() is not None
    assert not future_succeeded(future)


def test_future_succeeded_return_value_when_given_successful_futures() -> None:
    """:func:`future_succeeded` should return ``True`` when given a ``Future``
    that completed without any errors as it's input.
    """
    future: Future[int] = Future()
    future.set_result(10)

    assert future.result() == 10
    assert future_succeeded(future)


def test_type_fqn_return_value_on_first_party_types() -> None:
    """:func:`type_fqn` should return the correct full qualified name when
    given a first party (part of the current project) type or function.
    """
    assert type_fqn(Disposable) == "sghi.disposable.Disposable"
    assert (
        type_fqn(ResourceDisposedError)
        == "sghi.disposable.ResourceDisposedError"
    )
    assert type_fqn(not_disposed) == "sghi.disposable.not_disposed"
    assert type_fqn(type_fqn) == "sghi.utils.others.type_fqn"


def test_type_fqn_return_value_on_standard_lib_types() -> None:
    """:func:`type_fqn` should return the correct full qualified name when
    given a standard library type or function.
    """
    assert type_fqn(str) == "builtins.str"
    assert type_fqn(dict) == "builtins.dict"
    assert type_fqn(repr) == "builtins.repr"
    assert type_fqn(round) == "builtins.round"


def test_type_fqn_return_value_on_third_party_types() -> None:
    """:func:`type_fqn` should return the correct full qualified name when
    given a third party (third party library) type or function.
    """
    # FIXME: This might break on upgrade of pytest
    assert type_fqn(pytest.approx) == "_pytest.python_api.approx"
    assert type_fqn(pytest.importorskip) == "_pytest.outcomes.importorskip"
    assert type_fqn(pytest.raises) == "_pytest.python_api.raises"


def test_type_fqn_fails_on_none_input() -> None:
    """:func:`type_fqn` should raise a ``ValueError`` when given a ``None`` as
    it's input.
    """
    with pytest.raises(ValueError, match="MUST not be None") as exc_info:
        type_fqn(None)  # type: ignore

    assert exc_info.value.args[0] == "'klass' MUST not be None."
