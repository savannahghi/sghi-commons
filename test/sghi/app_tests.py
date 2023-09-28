import sghi.app
from sghi.config import Config


def test_conf_attribute() -> None:
    """
    :attr:`sghi.app.conf` should not be ``None`` and of type :class:`Config`.
    """

    assert isinstance(sghi.app.conf, Config)
