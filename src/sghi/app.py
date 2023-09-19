"""
Global state definitions for SGHI applications.

This module defines global properties important to an application. For all
intents and purposes, these properties should be treated and thought of as
constants. Any assignments to these properties should be done inside the
:func:`setup` function(see below).

This module also defines a single abstract function, :func:`setup`, whose main
purpose is to initialize and set up the application readying it for use. It
should be called early on before proceeding with the normal usage of the
application. The setup function defined here is abstract and thus not useful.
Applications should provide a valid implementation and monkey-patch it before
first use. Whether multiple calls to the ``setup`` should be allowed is not
defined and is left to the application implementors to decide.
"""
from collections.abc import Mapping, Sequence
from typing import Any, Final

from .config import Config, SettingInitializer

# =============================================================================
# GLOBAL APPLICATION/TOOL CONSTANTS
# =============================================================================


conf: Final[Config] = Config.of_proxy()
"""The application configurations.

.. important::

    A usable value is only available after a successful application set up.
    That is, after :func:`sghi.app.setup` or equivalent completes successfully.

.. admonition:: Note: To application authors
    :class: note

    This value is set to an instance of :class:`sghi.config.ConfigProxy`-
    enabling the default wrapped instance to be replaced with a more
    appropriate value during application setup.

"""


# =============================================================================
# SETUP FUNTION
# =============================================================================


def setup(
    settings: Mapping[str, Any] | None = None,
    settings_initializers: Sequence[SettingInitializer] | None = None,
    **kwargs,
) -> None:
    """Prepare the application and ready it for use.

    After this function completes successfully, the application should be
    considered set up and normal usage may proceed.

    .. important::

        This function is not implemented, and invocations will result in an
        exception being raised. Runtimes/implementing applications should
        monkey-patch this function before first use with a valid
        implementation.

    :param settings: An optional mapping of settings and their values. When not
        provided, the runtime defaults as well as defaults set by the given
        setting initializers will be used instead.
    :param settings_initializers: An optional sequence of setting initializers
        to execute during runtime setup.
    :param kwargs: Additional keyword arguments to pass to the implementing
        function.

    :return: None.
    """
    err_message = (
        "'setup' is not implemented. Implementing applications or tools "
        "should override this function with a suitable implementation."
    )  # pragma: no cover
    raise NotImplementedError(err_message)
