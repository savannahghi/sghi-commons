"""``Config`` interface definition, implementing classes and helpers."""

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from logging import Logger
from typing import TYPE_CHECKING, Any, Final, final

from ..exceptions import SGHIError
from ..task import Task, pipe
from ..utils import ensure_not_none, ensure_not_none_nor_empty, type_fqn

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Never


# =============================================================================
# TYPES
# =============================================================================


_Initializer_Factory = Callable[[], "SettingInitializer"]


# =============================================================================
# CONSTANTS
# =============================================================================


_INITIALIZERS_REGISTRY: Final[set[_Initializer_Factory]] = set()


# =============================================================================
# HELPERS
# =============================================================================


def get_registered_initializer_factories() -> Sequence[_Initializer_Factory]:
    """Return all registered :class:`SettingInitializer` factories or types.

    ``SettingInitializer`` types or their factories can be registered using
    the :func:`register` decorator.

    :return: A ``Sequence`` of all registered ``SettingInitializer`` types or
        factories.
    """
    return tuple(_INITIALIZERS_REGISTRY)


def register(f: _Initializer_Factory) -> _Initializer_Factory:
    """Register a setting initializer or it's factory.

    This decorator is used to mark
    :class:`setting initializers <SettingInitializer>` or their factories. The
    registered initializer factories can be accessed using the
    :func:`get_registered_initializer_factories` function.

    .. note::

        When used on a ``SettingInitializer`` type, the type's constructor
        MUST support zero args invocation.

    :param f: A ``SettingInitializer`` type or a factor function that returns
        ``SettingInitializer`` instances. This MUST not be ``None``.

    :return: The decorated target.

    :raises ValueError: If ``f`` is ``None``.
    """
    _INITIALIZERS_REGISTRY.add(ensure_not_none(f, "'f' MUST not be None."))
    return f


# =============================================================================
# EXCEPTIONS
# =============================================================================


class ConfigurationError(SGHIError):
    """Indicates a generic configuration error occurred."""

    def __init__(self, message: str | None = None):
        """Initialize a ``ConfigurationError`` with the given error message.

        :param message: An optional error message. A default will be used if
            one isn't provided.
        """
        _message: str = message or (
            "An unknown error occurred while configuring the app."
        )
        super().__init__(message=_message)


class ImproperlyConfiguredError(ConfigurationError):
    """Indicates that a configuration was found, but it is invalid."""


class NoSuchSettingError(ConfigurationError, LookupError):
    """Non-existent setting access error."""

    def __init__(self, setting: str, message: str | None = None) -> None:
        """Initialize a ``NoSuchSettingError`` with the given properties.

        :param setting: The missing setting. This MUST not be ``None`` or
            empty.
        :param message: An optional message for the resulting exception. If
            none is provided, then a generic one is automatically generated.

        :raise ValueError: If the specified setting name is ``None`` or empty.
        """
        self._setting: str = ensure_not_none_nor_empty(
            setting,
            "'setting' MUST not be None or empty.",
        )
        _message: str = message or f"Setting '{self._setting}' does not exist."
        ConfigurationError.__init__(self, message=_message)

    @property
    def setting(self) -> str:
        """The missing setting.

        This is the missing setting whose attempted access resulted in this
        exception being raised.

        :return: The missing setting.
        """
        return self._setting


class NotSetupError(ConfigurationError):
    """Indicates that the application is yet to be setup/initialized.

    Applications can be setup by calling the :meth:`sghi.app.setup` function or
    equivalent. Check the application documentation for more details.
    """

    def __init__(self, message: str | None = None):
        """Initialize a ``NotSetupError`` with the given error message.

        :param message: An optional error message. A default will be used if
            one isn't provided.
        """
        _message: str = message or (
            "Application not set up. Please call the 'sghi.app.setup()' "
            "function(or equivalent for the application) before proceeding."
        )
        super().__init__(message=_message)


class SettingRequiredError(ConfigurationError):
    """Indicates that a required setting wasn't provided.

    .. tip::

        :class:`SettingInitializer` implementations should raise this error to
        indicate that a required setting wasn't provided.
    """

    def __init__(self, setting: str, message: str | None = None) -> None:
        """Initialize a ``SettingRequiredError`` with the given properties.

        :param setting: The name of the setting that wasn't provided. This
            MUST not be ``None`` or empty.
        :param message: An optional message for the resulting exception. If
            none is provided, then a generic one is automatically generated.

        :raise ValueError: If the specified setting name is ``None`` or empty.
        """
        self._setting: str = ensure_not_none_nor_empty(
            setting,
            "'setting' MUST not be None or empty.",
        )
        _message: str = message or f"Setting '{self._setting}' is required."
        super().__init__(message=message)

    @property
    def setting(self) -> str:
        """The name of the setting that was not provided.

        :return: The setting that was not provided.
        """
        return self._setting


# =============================================================================
# SETTING INITIALIZER INTERFACE
# =============================================================================


class SettingInitializer(Task[Any, Any], metaclass=ABCMeta):
    """A :class:`~sghi.task.Task` used to initialize or validate a setting.

    This interface represents a ``Task`` used to perform some initialization
    action based on the value of a setting. This can include *(but is not
    limited to)* validating a given config value, setting up additional
    components, set default values for settings, etc.

    Setting initializers allow an application/tool to bootstrap/setup itself at
    startup. The only limitation is that they are only executed once, as part
    of the application's config instantiation.
    """

    __slots__ = ()

    @property
    def has_secrets(self) -> bool:
        """Indicates whether the value of this setting contains secrets or
        other sensitive data.

        This is important, and it indicates the value should be handled with
        special care to prevent accidental exposure of sensitive/private
        information.

        :return: ``True`` if the value of this setting contains secretes or
            ``False`` otherwise.
        """
        return False

    @property
    @abstractmethod
    def setting(self) -> str:
        """The setting to be initialized using this initializer.

        :return: The setting to be initialized using this initializer.
        """


# =============================================================================
# CONFIG INTERFACE
# =============================================================================


class Config(metaclass=ABCMeta):
    """An object that holds the application settings.

    Only read-only access to the settings is available post initialization. Any
    required modifications to the settings should be done at initialization
    time by passing a sequence of :class:`initializers<SettingInitializer>` to
    this class's :func:`of` factory method. Uppercase names for settings should
    be preferred to convey that they are read-only.

    Setting names that are also valid Python identifiers can be accessed using
    the dot notation on an instance of this class. The :meth:`get` method can
    also be used to access settings and is especially useful for access to
    settings with names that are invalid Python identifies.

    The ``in`` operator can be used to check for the presence of a setting in
    a given ``Config`` instance.

    .. tip::

        Unless otherwise indicated, at runtime, there should be an instance of
        this class at :attr:`sghi.app.conf` ment to hold the main
        configuration settings for the executing application.

    .. admonition:: Info: Regarding ``Config`` immutability

        This interface was intentionally designed with immutability in mind.
        The rationale behind this choice stems from the fact that, once loaded,
        configuration should rarely change if ever. This has a couple of
        benefits, chief among them being:

            - It makes it easy to reason about the application .i.e. you don't
              have to worry about the "current" configuration in use going
              stale.
            - It makes accessing and using the configuration safe in concurrent
              contexts.

        Nonetheless, making the configuration immutable also comes with some
        challenges. In most cases, configuration comes from the user inputs or
        external sources linked to the application. This necessitates a
        "loading" process from an origin, such as a disk. This typically
        happens during application setup or initiation phase. As such, there
        exists a (short) period between when the application starts and when
        the setup is concluded. During this phase, the application may not yet
        have a "valid" configuration.

        To account for such scenarios, there exists an implementation of this
        interface whose instances raises a :exc:`NotSetupError` whenever an
        attempt to access their settings is made. These instances function as
        the default placeholders for applications that have not undergone or
        are yet to complete the setup process. They can be created using the
        :func:`of_awaiting_setup` factory.
    """

    __slots__ = ()

    @abstractmethod
    def __contains__(self, __setting: str, /) -> bool:
        """Check if this ``Config`` instance contains the specified setting.

        :param __setting: The setting name to check for.

        :return: ``True`` if a setting with the given name is present in this
            ``Config``, ``False`` otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def __getattr__(self, __setting: str, /) -> Any:  # noqa: ANN401
        """Make settings available using the dot operator.

        :param __setting: The name of the setting value to retrieve.

        :raises NoSuchSettingError: If the setting is not present.

        :return: The value of the given setting if it is present in this
            config.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, setting: str, default: Any = None) -> Any:  # noqa: ANN401
        """Retrieve the value of the given setting or return the given default
        if no such setting exists in this ``Config`` instance.

        .. tip::

            This method can also be used for retrieval of settings with invalid
            Python identifier names.

        :param setting: The name of the setting value to retrieve.
        :param default: A value to return when no setting with the given name
            exists in this config.

        :return: The value of the given setting if it is present in this config
            or the given default otherwise.
        """
        raise NotImplementedError

    @staticmethod
    def of(
        settings: Mapping[str, Any],
        setting_initializers: Sequence[SettingInitializer] | None = None,
        skip_registered_initializers: bool = False,
    ) -> Config:
        """Create a new :class:`Config` instance.

        The settings to use are passed as a mapping with the setting names as
        the keys and the setting values as the values of the mapping.

        Optional :class:`initializers<SettingInitializer>` can also be passed
        to the factory to perform additional initialization tasks such as, set
        up of addition components, validating that required settings were
        provided, etc. Initializers can also be used to remap settings values
        to more appropriate runtime values by taking a raw setting value and
        returning the desired or appropriate value. The value is then set as
        the new value of the setting and will remain that way for the duration
        of the runtime of the application. If multiple initializers are given
        for the same setting, they are executed in the encounter order with the
        output of the previous initializer becoming the input of the next
        initializer. The output of the last initializer is then set as the
        final value of the setting.

        This factory will also include initializers marked using the
        :func:`register` decorator by default, .i.e, those returned by the
        :func:`get_registered_initializer_factories` function. This can be
        disabled by setting the ``skip_registered_initializers`` parameter to
        ``True``.

        :param settings: The configurations/settings to use as a mapping.
        :param setting_initializers: Optional initializers to perform
            post-initialization tasks.
        :param skip_registered_initializers: If ``True``, do not include
            initializers marked using the ``register`` decorator. Defaults to
            ``False``.

        :return: A `Config` instance.
        """
        initializers: list[SettingInitializer] = []
        if not skip_registered_initializers:
            registered_initializers = get_registered_initializer_factories()
            initializers.extend(
                initializer_factory()
                for initializer_factory in registered_initializers
            )
        initializers.extend(setting_initializers or ())
        return _ConfigImp(settings, settings_initializers=initializers)

    @staticmethod
    def of_awaiting_setup(err_msg: str | None = None) -> Config:
        """Create a new :class:`Config` instance to represent an application
        that is not yet set up.

        Any attempt to access settings from the returned instance will result
        in a :exc:`NotSetupError` being raised indicating to the user/caller
        that the application is yet to be setup.

        .. tip::

            Applications can be setup by calling the :func:`sghi.app.setup`
            function or equivalent. Check the application documentation for
            more details.

        :param err_msg: Optional custom error message to be displayed when
            accessing settings from the returned instance.

        :return: A new `Config` instance.
        """
        return _NotSetup(err_msg=err_msg)

    @staticmethod
    def of_proxy(
        source_config: Config | None = None,
        not_setup_err_msg: str | None = None,
    ) -> ConfigProxy:
        """Create a :class:`ConfigProxy` instance that wraps the given `Config`
        instance.

        If `source_config` is not given, it defaults to a value with similar
        semantics to those returned by the :meth:`Config.of_awaiting_setup`
        factory method. That is, a new value representing an application that
        is yet to be set up will be used.

        :param source_config: An optional ``Config`` instance to be wrapped by
            the returned ``ConfigProxy`` instance. Defaults to a ``Config``
            instance representing an application that is yet to be set up.
        :param not_setup_err_msg: An optional custom error message to be shown
            by the returned value in case ``source_config`` is ``None``.
            Ignored if ``source_config`` is not ``None``.

        :return: A new ``ConfigProxy`` instance.
        """
        return ConfigProxy(
            source_config or Config.of_awaiting_setup(not_setup_err_msg),
        )


# =============================================================================
# CONFIG IMPLEMENTATIONS
# =============================================================================


@final
class ConfigProxy(Config):
    """A :class:`Config` implementation that wraps other ``Config`` instances,
    facilitating whole configuration changes at runtime.

    The main advantage is it allows for lazy initialization of configuration
    without requiring references to a ``Config`` value to change. Changes to
    the wrapped ``Config`` instance can be made using the :meth:`set_source`
    method.

    .. caution::

        Configuration changes at runtime should be avoided unless necessary to
        minimize side effects and configurations going "stale". It is expected
        that most clients/users of the ``Config`` interface expect the
        configuration to remain unchanged at runtime. The only safe place to
        change the configuration is inside the
        :func:`application setup<sghi.app.setup>` function.
    """

    __slots__ = ("_source_config",)

    def __init__(self, source_config: Config) -> None:
        """Initialize a new :class:`ConfigProxy` instance that wraps the given
        source ``Config`` instance.

        :param source_config: The ``Config`` instance to wrap. This MUST not
            be ``None``.

        :raises ValueError: If ``source_config`` is None.
        """
        ensure_not_none(source_config, "'source_config' MUST not be None.")
        self._source_config: Config = source_config

    def __contains__(self, __setting: str, /) -> bool:
        """Check for the availability of a setting."""
        return self._source_config.__contains__(__setting)

    def __getattr__(self, __setting: str, /) -> Any:  # noqa: ANN401
        """Make settings available using the dot operator."""
        return self._source_config.__getattr__(__setting)

    def get(self, setting: str, default: Any = None) -> Any:  # noqa: ANN401
        return self._source_config.get(setting=setting, default=default)

    def set_source(self, source_config: Config) -> None:
        """Change the source configuration being wrapped by this proxy.

        :param source_config: The new source configuration to use. This MUST
            not be ``None``.

        :return: None.

        :raises ValueError: If ``source_config`` is None.
        """
        ensure_not_none(source_config, "'source_config' MUST not be None.")
        self._source_config: Config = source_config


@final
class _ConfigImp(Config):
    """A simple concrete implementation of the :class:`Config` interface."""

    __slots__ = ("_settings", "_initializers", "_logger")

    def __init__(
        self,
        settings: Mapping[str, Any],
        settings_initializers: Sequence[SettingInitializer] | None = None,
    ) -> None:
        """Initialize a new :class:`Config` instance.

        The settings to use are passed as a mapping with the setting names as
        the keys and the setting values as the values of the mapping.

        Optional initializers can also be passed to the constructor to perform
        additional initialization tasks such as set up of addition components
        or validating that required settings were provided, etc. Initializers
        can also be used to remap settings values to more appropriate runtime
        values by taking a raw setting value and return the desired or
        appropriate value. The value is then set as the new value of the
        setting and will remain that way for the duration of the runtime of the
        app. If multiple initializers are given for the same setting, they are
        executed in the encounter order with the output of the previous
        initializer becoming the input of the next initializer. The output of
        the last initializer is then set as the final value of the setting.

        :param settings: The configurations/settings to use as a mapping.
        :param settings_initializers: Optional initializers to perform
            post-initialization tasks.
        """
        self._settings: dict[str, Any] = dict(settings or {})
        self._initializers: Mapping[
            str,
            Sequence[SettingInitializer],
        ] = self._group_related_initializers(settings_initializers or ())
        self._logger: Logger = logging.getLogger(type_fqn(self.__class__))
        self._run_initializers()

    def __contains__(self, __setting: str, /) -> bool:
        """Check for the availability of a setting."""
        return self._settings.__contains__(__setting)

    def __getattr__(self, __setting: str, /) -> Any:  # noqa: ANN401
        """Make settings available using the dot operator."""
        try:
            return self._settings[__setting]
        except KeyError:
            raise NoSuchSettingError(setting=__setting) from None

    def get(self, setting: str, default: Any = None) -> Any:  # noqa: ANN401
        """Retrieve the value of the given setting or return the given default
        if no such setting exists in this ``Config`` instance.

        This method can also be used for retrieval of settings with invalid
        Python identifier names.

        :param setting: The name of the setting value to retrieve.
        :param default: A value to return when no setting with the given name
            exists in this config.

        :return: The value of the given setting if it is present in this config
            or the given default otherwise.
        """
        return self._settings.get(setting, default)

    def _run_initializers(self) -> None:
        """Run each setting initializer passing it the current raw value of the
        setting or ``None`` if the setting is not present.

        The return value of the initializer is set as the new value if the
        setting.
        This way, initializers can also be used to set default settings if
        they aren't already present.

        :return: None.
        """
        for _setting, _initializers in self._initializers.items():
            raw_setting_val: Any = self._settings.get(_setting)
            initializer_pipeline: pipe = pipe(*_initializers)
            setting_val: Any = initializer_pipeline(raw_setting_val)
            if self._logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
                self._logger.debug(
                    "Ran initializer for the setting '%s' with raw value '%s'.",  # noqa  :E502
                    str(_setting),
                    "******"
                    if any(_i.has_secrets for _i in _initializers)
                    else str(raw_setting_val),
                )
            self._settings[_setting] = setting_val

    @staticmethod
    def _group_related_initializers(
        initializers: Sequence[SettingInitializer],
    ) -> Mapping[str, Sequence[SettingInitializer]]:
        """Group the given initializers based on the setting they belong to.

        :param initializers: The list of initializers to group.
        :return: A dictionary containing the grouped initializers, where the
            keys are setting names, and the values are sequences of
            corresponding initializers.
        """
        grouped_initializers: dict[str, list[SettingInitializer]] = {}
        for _initializer in initializers:
            grouped_initializers.setdefault(_initializer.setting, []).append(
                _initializer,
            )
        return grouped_initializers


@final
class _NotSetup(Config):
    """A representation of an application that is not yet set up."""

    __slots__ = ("_err_msg",)

    def __init__(self, err_msg: str | None = None):
        """Initialize a new `_NotSetup` instance.

        :param err_msg: Optional custom error message to be displayed when
            accessing any setting.

        :return: None.
        """
        self._err_msg: str | None = err_msg

    def __contains__(self, __setting: str, /) -> bool:
        """Raise a ``NotSetupError`` when trying to check for the availability
        of a setting.

        :param __setting: The setting name to check for.

        :return: ``True`` if a setting with the given name is present in this
            ``Config``, ``False`` otherwise.
        """
        return self._raise(err_msg=self._err_msg)

    def __getattr__(self, __setting: str, /) -> Any:  # noqa: ANN401
        """Raise a ``NotSetupError`` when trying to access any setting.

        :param __setting: The name of the setting value to retrieve.

        :raises NotSetupError: Always raises the `NotSetupError`.

        :return: This method does not return a value; it raises an exception.
        """
        return self._raise(err_msg=self._err_msg)

    def get(self, setting: str, default: Any = None) -> Any:  # noqa: ANN401
        """Raise a ``NotSetupError`` when trying to access any setting.

        :param setting: The name of the setting value to retrieve.
        :param default: A value to return when no setting with the given name
            exists in this config.

        :raises NotSetupError: Always raises the `NotSetupError`.

        :return: This method does not return a value; it raises an exception.
        """
        return self._raise(err_msg=self._err_msg)

    @staticmethod
    def _raise(err_msg: str | None) -> Never:
        """Raise a `NotSetupError` with the specified error message.

        :param err_msg: An optional error message to be displayed in the
            exception.

        :raises NotSetupError: Always raises the `NotSetupError` with the
            specified error message.

        :return: This method does not return a value; it raises an exception.
        """
        raise NotSetupError(message=err_msg)


# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = [
    "Config",
    "ConfigurationError",
    "ConfigProxy",
    "ImproperlyConfiguredError",
    "NoSuchSettingError",
    "NotSetupError",
    "SettingInitializer",
    "SettingRequiredError",
    "get_registered_initializer_factories",
    "register",
]
