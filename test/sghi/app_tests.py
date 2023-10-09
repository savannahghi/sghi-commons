import sghi.app
from sghi.config import Config
from sghi.dispatch import Dispatcher


def test_conf_attribute() -> None:
    """
    :attr:`sghi.app.conf` should not be ``None`` and of type :class:`Config`.
    """

    assert isinstance(sghi.app.conf, Config)


def test_dispatcher_attribute() -> None:
    """
    :attr:`sghi.app.dispatcher` should not be ``None`` and of type
    :class:`Dispatcher`.
    """

    assert isinstance(sghi.app.dispatcher, Dispatcher)
