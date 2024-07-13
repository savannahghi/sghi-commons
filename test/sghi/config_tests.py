from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest import TestCase

import pytest
from typing_extensions import override

from sghi.config import (
    Config,
    ConfigProxy,
    ImproperlyConfiguredError,
    NoSuchSettingError,
    NotSetupError,
    SettingInitializer,
    SettingRequiredError,
    get_registered_initializer_factories,
    register,
    setting_initializer,
)
from sghi.utils import ensure_predicate

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# =============================================================================
# TESTS HELPERS
# =============================================================================


@register
@setting_initializer(setting="DB_USERNAME")
def db_username_initializer(username: str | None) -> str:
    return username or "postgres"


@register
class DBPortInitializer(SettingInitializer):
    __slots__ = ()

    @property
    @override
    def setting(self) -> str:
        return "DB_PORT"

    @override
    def execute(self, an_input: int | str | None) -> int:
        match an_input:
            case None:
                return 5432
            case int():
                return self._ensure_valid_port(an_input)
            case str() if an_input.isdigit():
                return self._ensure_valid_port(int(an_input))
            case _:
                _err_msg: str = (
                    "'DB_PORT' MUST be an integer or string containing "
                    "digits only."
                )
                raise ImproperlyConfiguredError(message=_err_msg)

    @staticmethod
    def _ensure_valid_port(port: int) -> int:
        ensure_predicate(
            0 <= port <= 65536,
            message=f"Invalid port {port}. Out of range!!",
            exc_factory=ImproperlyConfiguredError,
        )
        return port


class DBPasswordInitializer(SettingInitializer):
    __slots__ = ()

    @property
    @override
    def has_secrets(self) -> bool:
        return True

    @property
    @override
    def setting(self) -> str:
        return "DB_PASSWORD"

    @override
    def execute(self, an_input: str | None) -> str:
        if not an_input:
            _err_msg: str = f"'{self.setting}' is required."
            raise SettingRequiredError(self.setting, message=_err_msg)

        return an_input


# =============================================================================
# TESTS
# =============================================================================


def test_get_registered_initializer_factories_return_value() -> None:
    """:func:`get_registered_initializer_factories` should return all
    initializer factories decorated using the :func:`register` decorator.
    """
    assert len(get_registered_initializer_factories()) == 2
    for init_factory in get_registered_initializer_factories():
        assert isinstance(init_factory(), SettingInitializer)


def test_setting_initializer_return_value() -> None:
    """:func:`setting_initializer` should return a factory function that
    supplies ``SettingInitializer`` instances with the same properties as those
    supplied on the decorator and the same semantics as the decorated function.
    """

    @setting_initializer(setting="USERNAME", has_secrets=True)
    def username_initializer(username: str | None) -> str:
        if not username:
            _err_msg: str = "'USERNAME' MUST NOT be a None nor empty string."
            raise SettingRequiredError(setting="USERNAME", message=_err_msg)
        return username

    initializer1: SettingInitializer = username_initializer()
    initializer2: SettingInitializer = db_username_initializer()

    assert isinstance(initializer1, SettingInitializer)
    assert isinstance(initializer2, SettingInitializer)
    assert initializer1.has_secrets
    assert not initializer2.has_secrets
    assert initializer1.setting == "USERNAME"
    assert initializer2.setting == "DB_USERNAME"

    assert initializer1("C-3PO") == "C-3PO"
    with pytest.raises(SettingRequiredError) as exc_info:
        initializer1(None)
    assert exc_info.value.setting == "USERNAME"

    assert initializer2(None) == "postgres"
    assert initializer2("app-db-admin") == "app-db-admin"


class TestConfig(TestCase):
    """
    Tests of the :class:`Config` interface default method implementations.
    """

    def setUp(self) -> None:
        super().setUp()
        self._settings: Mapping[str, str] = {"DB_PASSWORD": "s3c3r3PA55word!"}
        self._setting_initializers: Sequence[SettingInitializer] = [
            DBPasswordInitializer(),
        ]

    def test_of_factory_method_return_value(self) -> None:
        """
        :meth:`Config.of` should return a ``Config`` instance created from the
        given settings and setting initializers.
        """
        config1: Config = Config.of(
            settings=self._settings,
            setting_initializers=self._setting_initializers,
        )
        config2: Config = Config.of(
            settings=self._settings,
            setting_initializers=self._setting_initializers,
            skip_registered_initializers=True,
        )
        config3: Config = Config.of({})
        config4: Config = Config.of({}, skip_registered_initializers=True)

        assert config1 is not None
        assert "DB_PASSWORD" in config1
        assert "DB_PORT" in config1  # Added by the DBPortInitializer
        assert config1.DB_PASSWORD == "s3c3r3PA55word!"  # noqa: S105
        assert config1.get("DB_PORT") == 5432

        assert config2 is not None
        assert "DB_PASSWORD" in config2
        assert "DB_PORT" not in config2
        assert config2.DB_PASSWORD == "s3c3r3PA55word!"  # noqa: S105
        assert config2.get("DB_PORT") is None

        assert config3 is not None
        assert "DB_PASSWORD" not in config3
        assert "DB_PORT" in config3
        assert config3.get("DB_PASSWORD") is None
        assert config3.DB_PORT == 5432

        assert config4 is not None
        assert "DB_PASSWORD" not in config4
        assert "DB_PORT" not in config4
        assert config4.get("DB_PASSWORD") is None
        assert config4.get("DB_PORT") is None

        with pytest.raises(SettingRequiredError) as exc_info:
            Config.of(
                settings={},
                setting_initializers=self._setting_initializers,
            )

        assert exc_info.value.message == "'DB_PASSWORD' is required."
        assert exc_info.value.setting == "DB_PASSWORD"

    def test_of_awaiting_setup_factory_method_return_value(self) -> None:
        """:meth:`Config.of_awaiting_setup` should return a ``Config`` instance
        that raises ``NotSetupError`` on any attempted access to its settings.
        """
        config1: Config = Config.of_awaiting_setup()
        config2: Config = Config.of_awaiting_setup(err_msg="Setup required!!!")

        assert config1 is not None
        with pytest.raises(NotSetupError, match="Application not set up"):
            "DB_PORT" in config1  # noqa  # type: ignore

        with pytest.raises(NotSetupError, match="Application not set up"):
            getattr(config1, "DB_PASSWORD", None)

        with pytest.raises(NotSetupError, match="Application not set up"):
            config1.get("DB_PORT")

        assert config2 is not None
        with pytest.raises(NotSetupError, match="Setup required!!!"):
            "DB_PORT" in config2  # noqa  # type: ignore

        with pytest.raises(NotSetupError, match="Setup required!!!"):
            getattr(config2, "DB_PASSWORD", None)

        with pytest.raises(NotSetupError, match="Setup required!!!"):
            config2.get("DB_PORT")

    def test_of_proxy_factory_method_return_value(self) -> None:
        """
        :meth:`Config.of_proxy` should return a ``ConfigProxy`` instance that
        wraps the given source ``Config`` instance or a ``Config`` instance
        that represents an application that is not set up when a source
        ``Config`` is not provided.
        """
        config1: Config = Config.of_proxy()
        config2: Config = Config.of_proxy(not_setup_err_msg="Setup required!")
        config3: Config = Config.of_proxy(
            Config.of(self._settings, self._setting_initializers),
        )

        assert isinstance(config1, ConfigProxy)
        with pytest.raises(NotSetupError, match="Application not set up"):
            "DB_PORT" in config1  # noqa  # type: ignore

        assert isinstance(config2, ConfigProxy)
        with pytest.raises(NotSetupError, match="Setup required!"):
            "DB_PORT" in config2  # noqa  # type: ignore

        assert isinstance(config3, ConfigProxy)
        assert "DB_PORT" in config3
        assert config3.DB_PORT == 5432

    def test_of_proxy_err_msg_ignored_when_source_config_is_not_none(
        self,
    ) -> None:
        """:meth:`Config.of_proxy` should ignore the ``not_setup_err_msg``
        parameter if the corresponding ``source_config`` parameter is not
        ``None``.
        """
        config: Config = Config.of_proxy(
            source_config=Config.of_awaiting_setup(err_msg="Not yet!!"),
            not_setup_err_msg="Setup required!",
        )

        # The err_msg "Set required!" should be ignored since 'source_config'
        # is not None.
        with pytest.raises(NotSetupError, match="Not yet!!"):
            config.get("DB_PORT")


class TestConfigProxy(TestCase):
    """Tests for the :class:`ConfigProxy` class."""

    def setUp(self) -> None:
        super().setUp()
        self._source_config: Config = Config.of(
            settings={"DB_PASSWORD": "s3c3r3PA55word!"},
            setting_initializers=[DBPasswordInitializer()],
        )
        self._instance: ConfigProxy = ConfigProxy(self._source_config)

    def test_init_fails_on_none_input_value(self) -> None:
        """:meth:`ConfigProxy.__init__` should raise a :exc:`ValueError` when
        given a ``None`` ``source_config``.
        """
        with pytest.raises(ValueError, match="config' MUST not be None"):
            ConfigProxy(source_config=None)  # type: ignore

    def test_dunder_contains_return_value(self) -> None:
        """:meth:`ConfigProxy.__contains__` should return the same value as its
        wrapped ``Config`` value.
        """
        assert "DB_PORT" in self._source_config
        assert "DB_PORT" in self._instance
        assert "DB_PASSWORD" in self._source_config
        assert "DB_PASSWORD" in self._instance
        assert "DB_NAME" not in self._source_config
        assert "DB_NAME" not in self._instance

    def test_dunder_getattr_return_value(self) -> None:
        """:meth:`ConfigProxy.__getattr__` should return the same value as its
        wrapped ``Config`` value.
        """
        assert self._source_config.DB_PORT == 5432
        assert self._instance.DB_PORT == 5432
        assert self._source_config.DB_PASSWORD == "s3c3r3PA55word!"  # noqa: S105
        assert self._instance.DB_PASSWORD == "s3c3r3PA55word!"  # noqa: S105

    def test_dunder_getattr_fails_on_missing_setting(self) -> None:
        """
        :meth:`ConfigProxy.__getattr__` should raise :exc:`NoSuchSettingError`
        if access to non-existing setting on the wrapped ``Config`` value is
        made.
        """
        with pytest.raises(NoSuchSettingError) as exc_info:
            self._instance.DB_NAME  # noqa B018

        assert exc_info.value.setting == "DB_NAME"

    def test_get_method_return_value(self) -> None:
        """:meth:`ConfigProxy.get` should return the same value as its wrapped
        ``Config`` value.
        """
        source: Config = self._source_config
        instan: Config = self._instance

        assert source.get("DB_PORT") == instan.get("DB_PORT") == 5432
        assert (
            source.get("DB_PASSWORD")
            == instan.get("DB_PASSWORD")
            == "s3c3r3PA55word!"
        )
        assert source.get("DB_NAME") is instan.get("DB_NAME") is None

    def test_set_source_method_side_effects(self) -> None:
        """:meth:`Config.set_source` should swap the wrapped source ``Config``
        instance to the new provided value.
        """
        self._instance.set_source(
            Config.of({}, skip_registered_initializers=True),
        )

        assert "DB_PORT" not in self._instance
        assert "DB_PASSWORD" not in self._instance
        assert "DB_NAME" not in self._instance

    def test_set_source_method_fails_on_none_input_value(self) -> None:
        """
        :meth:`Config.set_source` should raise :exc:``ValueError`` when given
        a ``None`` source ``Config`` instance as input.
        """
        with pytest.raises(ValueError, match="config' MUST not be None."):
            self._instance.set_source(source_config=None)  # type: ignore


class TestSettingInitializer(TestCase):
    """Tests for the :SettingInitializer: interface default implementations."""

    def test_has_secrets_return_value(self) -> None:
        """The default implementation of :attr:`SettingInitializer.has_secrets`
        should evaluate to ``False``.
        """

        class SomeInitializer(SettingInitializer):
            """A :class:`SettingInitializer` implementation that relies on the
            default :attr:`SettingInitializer.has_secrets` implementation.
            """

            @property
            def setting(self) -> str:
                return "SOME_SETTING"

            def execute(self, an_input: Any) -> Any:  # noqa: ANN401
                ...

        assert not SomeInitializer().has_secrets
