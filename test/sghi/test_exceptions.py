from unittest import TestCase

from sghi.exceptions import SGHIError


class TestSGHIError(TestCase):
    """Tests for the ``SGHIError`` class."""

    def test_message_prop_return_value(self) -> None:
        """Ensure the ``message`` property returns the expected value."""

        error1 = SGHIError(message="Fatal error.")
        error2 = SGHIError()

        assert error1.message == "Fatal error."
        assert error2.message is None

    def test_str_representation(self) -> None:
        """Ensure the string representation of an ``SGHIError`` is correct."""

        error1 = SGHIError(message="Fatal error :(")
        error2 = SGHIError()

        assert str(error1) == "Fatal error :("
        assert str(error2) == ""
