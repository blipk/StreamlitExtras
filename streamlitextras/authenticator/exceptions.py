# Exceptions for the firebase auth helper in autenticator.py
from typing import Union, Optional
from requests import HTTPError


class AuthException(Exception):
    """
    Base exception for Authenticator class
    """

    def __init__(
        self,
        message: str,
        firebase_error: Optional[str] = None,
        requests_exception: Optional[Union[HTTPError, Exception]] = None,
    ):
        """
        :param str message: message to be displayed to the user
        :param Optional[str] firebase_error: firebase error message enum e.g INVALID_PASSWORD
        :param Union[HTTPError, Exception] requests_exception: requests.HTTPError with .response and .request attributes (or other associated exception)
        """
        self.message = message
        self.firebase_error = firebase_error
        self.requests_exception = requests_exception


class LoginError(AuthException):
    """Exceptions raised for the login user widget."""


class RegisterError(AuthException):
    """Exceptions raised for the register user widget."""


class ResetError(AuthException):
    """Exceptions raised for the rest password widget."""


class UpdateError(AuthException):
    """Exceptions raised for the update user details widget."""
