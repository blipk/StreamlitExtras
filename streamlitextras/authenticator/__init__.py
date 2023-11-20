import jwt
import pytz
import time
import dateutil.parser
from types import ModuleType
from typing import Union, Optional, Tuple, TypeVar, Type, Callable
from datetime import datetime, timedelta
from http.cookies import SimpleCookie

import streamlit as st
from streamlit.web.server.websocket_headers import _get_websocket_headers
from streamlit.delta_generator import DeltaGenerator
from streamlitextras.logger import log
from streamlitextras.utils import repr_
from streamlitextras.authenticator.user import User
from streamlitextras.authenticator.exceptions import (
    AuthException,
    LoginError,
    RegisterError,
    ResetError,
    UpdateError,
)
from streamlitextras.authenticator.utils import handle_firebase_action
from streamlitextras.webutils import get_user_timezone
from streamlitextras.cookiemanager import get_cookie_manager

import json
import requests
import pyrebase
import firebase_admin
from firebase_admin import auth as service_auth
from streamlitextras.helpers import custom_html

config = dict(st.secrets["firebase"])
pyrebase_service = pyrebase.initialize_app(config)
auth = pyrebase_service.auth()
db = pyrebase_service.database()
storage = pyrebase_service.storage()


# PyPI doesn't contain the latest git commits for pyrebase4
def update_profile(
    id_token, display_name=None, photo_url=None, delete_attribute=None, *args
):
    """
    Pyrebase on PyPI seems to be missing latest commits - adding this in here.
    https://firebase.google.com/docs/reference/rest/auth#section-update-profile
    """
    request_ref = (
        "https://identitytoolkit.googleapis.com/v1/accounts:update?key={0}".format(
            auth.api_key
        )
    )
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps(
        {
            "idToken": id_token,
            "displayName": display_name,
            "photoURL": photo_url,
            "deleteAttribute": delete_attribute,
            "returnSecureToken": True,
        }
    )
    request_object = requests.post(request_ref, headers=headers, data=data)
    pyrebase.pyrebase.raise_detailed_error(request_object)
    return request_object.json()


auth.update_profile = update_profile

UserInherited = TypeVar("UserInherited", bound="User", covariant=True)


class Authenticator:
    """
    Authenticator is used to handle firebase authentication,
    as well as create streamlit widgets for login, registration,
    and other account operations.

    :param str authenticator_name: named key for this Authenticator class, used to store it in session state. Used for tracking without classvar reference.
    :param str cookie_name: the name of the auth cookie to be saved in the browser
    :param str cookie_key: the key used to encrypt the JWT stored in the auth cookie
    :param str session_name: the name of the key to store in st.session_state and the JWT token (with exp_date), containing the decoded auth cookie to
    :param UserInherited user_class: Optional inherited User class to store the User state in
    :param list admins_ids:
        List of firebase user ids (localId) used for checking User.is_admin
        Can also be | seperated string that will be parsed to a list - useful for parsing from a secrets config file
    :param list developer_ids:
        List of firebase user ids (localId) used for checking User.is_developer
        Can also be | seperated string that will be parsed to a list - useful for parsing from a secrets config file
    :param bool require_email_verification: If set to True (the default), users will not be able to log in until they verify their email address
    """

    def __init__(
        self,
        cookie_name: str,
        cookie_key: str,
        session_expiry_seconds: int = 3600 * 24 * 12,
        session_name: str = "user",
        authenticator_name: str = "authenticator",
        user_class: Optional[Type[UserInherited]] = None,
        admin_ids: Optional[Union[list, str]] = None,
        developer_ids: Optional[Union[list, str]] = None,
        require_email_verification: bool = True,
        attempt_fallback_cookies: bool = False,
        debug: bool = False,
    ):
        self.debug = debug

        if authenticator_name == session_name:
            raise ValueError(
                "authenticator_name can't be the same as session_name (st.session_state conflict)"
            )

        if not user_class:
            user_class = User

        self.cookie_name = cookie_name
        self.session_name = session_name
        self.session_expiry_seconds = session_expiry_seconds
        self.authenticator_name = authenticator_name
        self.cookie_key = cookie_key
        self.last_user = None
        self.user_class = user_class
        self.require_email_verification = require_email_verification
        self.attempt_fallback_cookies = attempt_fallback_cookies

        self.storage = storage
        self.auth = auth
        self.db = db

        self.logged_out = None

        if not admin_ids:
            admin_ids = []
        if type(admin_ids) not in [str, list]:
            raise ValueError("admin_ids must be a list or a | seperated string")
        self.admin_ids = admin_ids.split("|") if type(admin_ids) == str else admin_ids

        if not developer_ids:
            developer_ids = []
        if type(developer_ids) not in [str, list]:
            raise ValueError("developer_ids must be a list or a | seperated string")
        self.developer_ids = (
            developer_ids.split("|") if type(developer_ids) == str else developer_ids
        )

        # Streamlit refreshes a lot recreating this class - keep the same form between refreshes
        self.current_form = None
        if (
            self.authenticator_name in st.session_state
            and st.session_state[self.authenticator_name]
            and st.session_state[self.authenticator_name].current_form
        ):
            self.current_form = st.session_state[self.authenticator_name].current_form

        self.service_credentials = firebase_admin.credentials.Certificate(
            dict(st.secrets["gcp_service_account"])
        )
        try:
            self.firebase_service = firebase_admin.get_app()
        except ValueError as e:
            self.firebase_service = firebase_admin.initialize_app(
                self.service_credentials
            )

        if self.session_name not in st.session_state:
            st.session_state[self.session_name] = None
        if "authentication_token" not in st.session_state:
            st.session_state["authentication_token"] = None
        if "login_message" not in st.session_state:
            st.session_state["login_message"] = None
        if self.authenticator_name not in st.session_state:
            st.session_state[self.authenticator_name] = self
        st.session_state[self.authenticator_name] = self

        self.user_tz = None
        self.cookie_manager = get_cookie_manager()
        if self.debug:
            log.debug(f"Initialized Authenticator {hex(id(self))}")

    def delayed_init(self):
        """
        Used to delay initialization of streamlit objects so this class can be cached
        """
        if self.session_name not in st.session_state:
            st.session_state[self.session_name] = None

        if "authentication_token" not in st.session_state:
            st.session_state["authentication_token"] = None

        if "login_message" not in st.session_state:
            st.session_state["login_message"] = None

        st.session_state[self.authenticator_name] = self

        if not self.user_tz:
            self.user_tz = get_user_timezone(default_tz="Australia/Sydney")

        # if not self.cookie_manager:
        self.cookie_manager.delayed_init()

    @property
    def service_auth(self) -> Optional[ModuleType]:
        user = self.current_user
        if not user or not user.is_admin:
            return None
        else:
            return service_auth

    @property
    def current_user(self) -> Optional[UserInherited]:
        """
        Returns a User interface class instance if there is an active login
        """
        current_user = None
        if self.last_user:
            current_user = self.last_user
        elif (
            self.session_name in st.session_state
            and st.session_state[self.session_name]
        ):
            current_user = st.session_state[self.session_name]

        self.last_user = current_user
        return current_user

    @property
    def auth_cookie(self) -> Optional[str]:
        """
        Gets the auth cookie

        :returns: Returns the auth cookie or None if it doesnt exist
        """
        if (
            "authentication_token" in st.session_state
            and st.session_state["authentication_token"]
        ):
            auth_cookie = st.session_state["authentication_token"]
            return auth_cookie

        cookie = None
        headers = _get_websocket_headers()
        if not headers:
            return cookie

        cookie_header = headers.get("Cookie", None) or headers.get("cookie", None)
        cookie_reader = SimpleCookie(cookie_header)

        cookie = cookie_reader.get(self.cookie_name, None)
        if cookie is not None and cookie.value:
            cookie = cookie.value
        elif self.attempt_fallback_cookies:
            # Try cookie manager component instead of websocket headers
            cookie = self.cookie_manager.get(self.cookie_name)
            cookie = cookie or None  # cookie_manager.get returns None or {}

        return cookie

    def _revoke_auth(
        self, error: Optional[AuthException] = None, disabled: bool = False
    ) -> bool:
        """
        Deletes the auth cookie and revokes any firebase tokens

        :param Optional[AuthException] error: Optional associated error message for the revoke
        :param bool disabled: Optional flag to block execution of this routine. Default is False.

        :returns bool: Always returns False unless an unhandled error is raised
        """
        if disabled:
            log.warning("Authenticator._revoke_auth() disabled")
            return

        msg = error.message if error else ""
        error_type = error.firebase_error if error else ""
        user = self.current_user
        user_display = user.localId if user else "no current_user"
        log.info(f"Revoking cookie for {user_display}: {msg} {error_type}")
        self.cookie_manager.delete(self.cookie_name)

        # If the revokation wasn't from an already expired token, revoke current refresh tokens for user
        if self.last_user and (
            not error or (error and error.firebase_error != "TOKEN_EXPIRED")
        ):
            try:
                service_auth.revoke_refresh_tokens(self.last_user.localId)
                log.info(f"Firebase tokens revoked for {self.last_user.localId}")
            except service_auth.UserNotFoundError:
                log.warning("Couldn't invalidate session. UserNotFoundError")

        # Delete cookie and reset vars
        st.session_state[self.session_name] = None
        st.session_state["authentication_token"] = None
        self.last_user = None
        self.logged_out = True
        self.set_form("login")
        log.warning(f"Logged out {user_display}")
        self.cookie_manager.delete(self.cookie_name)
        # self.cookie_manager.set(self.cookie_name, "", datetime.fromtimestamp(0))

        return False

    @property
    def auth_status(self) -> bool:
        """
        First checks for any valid authentication cookies,
        then returns the current authentication status,
        True if a user is Authenticated, or else False.

        :returns bool: The authentication status
        """
        error = None
        status = False

        if (
            self.current_user
            and st.session_state[self.session_name]
            and st.session_state["authentication_token"]
        ):
            return True

        status, error, session_cookie, decoded_claims = self._check_cookie()
        if error:
            if "Invalid Session Cookie" in str(error) and not self.logged_out:
                log.error(error)
                self._revoke_auth(error)

            return False

        user = None
        if status:
            if (
                self.session_name in st.session_state
                and st.session_state[self.session_name]
            ):
                user = st.session_state[self.session_name]
            if not user:
                user = self._initialize_user_session(session_cookie, decoded_claims)
                if user:
                    self.set_form(None)
                else:
                    error = AuthException("Unable to initialize user")
                    status = None
        else:
            if not self.current_form:
                self.set_form("login")
        self.logged_out = not status
        return status

    def _check_cookie(self) -> tuple[bool, AuthException, str, dict]:
        """
        Looks for a cookie named self.cookie_name and checks its validity
        If it is valid, it returns the session cookie along with decoded claims

        :returns tuple[bool, AuthException, dict]:
            (status, error, session_cookie, decoded_claims)
            status is True if the claims are validated
            error will have any errors
            session_cookie and it's decoded_claims will be set if status is True
        """
        status = False
        error = None
        session_cookie = None
        decoded_claims = None

        if self.logged_out is True:
            return (status, error, session_cookie, decoded_claims)

        session_cookie = self.auth_cookie
        if not session_cookie:
            error = AuthException("No session cookie found")
            return (status, error, session_cookie, decoded_claims)

        try:
            decoded_claims = service_auth.verify_session_cookie(
                session_cookie, check_revoked=True
            )
            if decoded_claims and "user_id" in decoded_claims:
                status = True
                error = None
        except service_auth.InvalidSessionCookieError as e:
            error = AuthException("Invalid Session Cookie")
            return (status, error, session_cookie, decoded_claims)

        if error:
            log.error(f"Unexpected failure in when checking cookie {error}")

        return (status, error, session_cookie, decoded_claims)

    def _initialize_user_session(
        self,
        session_cookie: str,
        decoded_claims: dict,
        login_data: Optional[dict] = None,
        set_cookie_expires_in: Optional[timedelta] = None,
    ) -> Optional[UserInherited]:
        """
        Initialize the users session state after login or reading cookie.
        The cookie and data must be validated before this function.

        :param user: Instance of self.user_class
        :param str session_cookie: the users session cookie
        :param dict decoded_claims: the decoded claims from when verifying login idToken or session cookie
        :param Optional[dict] login_data:
            Account data with idtoken and refresh token returned from pyrebase login handler.
        :param Optional[timedelta] set_cookie_expires_in:
            If you want to write the session to the cookie as well, provide this (it's expiry from now in users tz)

        :returns Optional[UserInherited]:
            Returns the User created
        """
        user = None
        if "user_id" in decoded_claims:
            user_id = decoded_claims["user_id"]
        else:
            user_id = login_data["idToken"]

        user_record = service_auth.get_user(user_id)
        user_record_cleaned = user_record._data
        user_record_cleaned["passwordHash"] = ""
        auth_data = {
            "session_cookie": session_cookie,
            "decoded_claims": decoded_claims,
            "user_record": user_record_cleaned,
        }
        if not login_data:
            login_data = {}
        user = self.user_class(self, auth_data=auth_data, login_data=login_data)

        if user.is_admin:
            service_auth.set_custom_user_claims(user.localId, {"admin": True})
        if user.is_developer:
            service_auth.set_custom_user_claims(user.localId, {"devops": True})
        self.last_user = user

        st.session_state["authentication_token"] = session_cookie
        st.session_state[self.session_name] = user

        if set_cookie_expires_in:
            cookie_expiry_time = (
                datetime.now().astimezone(tz=pytz.timezone(self.user_tz))
                + set_cookie_expires_in
            )
            self.cookie_manager.set(
                self.cookie_name, session_cookie, expires_at=cookie_expiry_time
            )
        log.success(
            f"Initialized session{' and set cookie' if set_cookie_expires_in else ''} {user}"
        )
        return user

    def _create_session(
        self, login_data: dict, expires_in: Optional[timedelta] = None
    ) -> Tuple[Optional[UserInherited], Optional[LoginError]]:
        """
        Creates a User from firebase token data and instantiates a session for them.
        This is used on login.

        :param dict login_data:
            The firebase data to construct the User for the session from - used on login
        :param Optional[timedelta] expires_in:
            a timedelta for how long until the session cookie expires,
            defaults to current time (in user tz) plus self.session_expiry_seconds

        :returns tuple: (user, error) - A user if one was created, and any errors in the operation
        """
        user = None
        error = None
        if not expires_in:
            expires_in = timedelta(seconds=self.session_expiry_seconds)

        id_token = login_data["idToken"]
        try:
            decoded_claims = service_auth.verify_id_token(id_token)
            # Only process if the user signed in within the last 5 minutes.
            if time.time() - decoded_claims["auth_time"] < 5 * 60:
                session_cookie = service_auth.create_session_cookie(
                    id_token, expires_in=expires_in
                )
                user = self._initialize_user_session(
                    session_cookie,
                    decoded_claims,
                    login_data,
                    set_cookie_expires_in=expires_in,
                )
                if not user:
                    error = LoginError("Please try again.")
            else:
                error = LoginError("Expired credentials")
        except (
            service_auth.InvalidIdTokenError,
            service_auth.ExpiredIdTokenError,
            service_auth.RevokedIdTokenError,
            service_auth.CertificateFetchError,
            service_auth.UserDisabledError,
        ):
            error = LoginError("Expired credentials")
        except firebase_admin.exceptions.FirebaseError:
            error = LoginError("Please try again.")

        return (user, error)

    def _check_credentials(
        self, email: str, password: str
    ) -> Tuple[Optional[dict], Optional[LoginError], Optional[dict], bool]:
        """
        Checks the validity of the entered credentials, and if the accounts email is verified.

        :returns tuple: (res, error, login_data, validated)
            res and error are responses and errors from firebase
            login_data and boolean validated are set if the credentials pass
        """
        res = None
        error = None
        login_data = None
        validated = False
        signin_errors = {
            "INVALID_EMAIL": "Invalid email format",
            "EMAIL_NOT_FOUND": "Email address is not registered",
            "INVALID_PASSWORD": "Invalid password",
        }
        res, error = handle_firebase_action(
            auth.sign_in_with_email_and_password,
            LoginError,
            signin_errors,
            email,
            password,
        )
        account_info = None
        user_refresh = None
        if not error:
            refresh_errors = {
                "TOKEN_EXPIRED": "Too many recent sessions. Please try again later."
            }
            user_refresh, error = handle_firebase_action(
                auth.refresh, LoginError, refresh_errors, res["refreshToken"]
            )
            if not error:
                res = {**res, **user_refresh}

        if not error:
            account_info, error = handle_firebase_action(
                auth.get_account_info, LoginError, False, res["idToken"]
            )

        if not error:
            if (
                self.require_email_verification
                and account_info
                and not account_info["users"][0]["emailVerified"]
            ):
                error = LoginError("Please verify your email address before logging in")
                st.button(
                    "Resend verification email",
                    on_click=self._resend_verification,
                    args=(res["idToken"],),
                )

        if res and not error:
            if account_info:
                login_data = res
                account_info["users"][0]["passwordHash"] = ""
                login_data["account_info"] = account_info
                validated = True
            else:
                error = LoginError("Error retrieving account info")

        return (res, error, login_data, validated)

    def _resend_verification(
        self, user_id_token: str
    ) -> Tuple[Optional[dict], Optional[AuthException]]:
        """
        Resends the firebase auth verification email for a user

        :param user_id_token: The authenticated firebase auth token for the user with an unverified email address

        :returns: tuple containing the firebase response and any errors
        """
        res = None
        error = None
        resend_errors = {
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts, try again later."
        }
        res, error = handle_firebase_action(
            auth.send_email_verification, AuthException, resend_errors, user_id_token
        )

        if error:
            # st.error(error)
            st.session_state["login_message"] = error
        else:
            # st.info("Verification email sent")
            st.session_state[
                "login_message"
            ] = "Verification email sent, please check your inbox."

        return (res, error)

    def set_form(self, form_name: Optional[str]) -> None:
        """
        Sets a variable to keep track of which form is currently displayed.

        "login" = Login form
        "register" = Registration form
        "reset_password" = Reset password form
        """
        self.current_form = form_name

    def logout(
        self,
        button_name: str,
        button_location: Union[DeltaGenerator, ModuleType] = st.sidebar,
        disabled: bool = False,
    ) -> bool:
        """
        Creates a logout button.

        :param str button_name: The rendered name of the logout button.
        :param Union[DeltaGenerator, ModuleType] button_location: The streamlit container to place the button. Either global `st` or a st container object such as st.sidebar.
        :param bool disabled: Passed to the streamlit button disabled kwarg, to optional disable the button in some circumstances. Default is False.

        :returns bool: Returns True when clicked
        """

        if not isinstance(button_location, DeltaGenerator) and button_location != st:
            raise ValueError(
                "Location must be a streamlit DeltaGenerator (st container object such as st.sidebar) or the global st module."
            )

        if button_location.button(
            button_name,
            disabled=disabled,
            on_click=self._revoke_auth,
            args=(
                AuthException("Logout requested"),
                disabled,
            ),
            key=f"authenticator_logout_btn_{time.time()}",
        ):
            return True

        return False

    def login(
        self,
        form_name: str,
        form_location: Union[DeltaGenerator, ModuleType] = st,
        success_callback: Optional[Callable] = None,
        cb_args: Optional[tuple] = None,
        cb_kwargs: Optional[dict] = None,
    ) -> Tuple[Optional[UserInherited], dict, Optional[LoginError]]:
        """
        Creates a login widget.

        :param str form_name: The rendered name of the login form.
        :param Union[DeltaGenerator, ModuleType] form_location: The streamlit container to place the form. Either global `st` or a st container object such as st.sidebar.
        :param Callable success_callback:
            Optional function to call if a user is created without error.
            Will be passed a kwargs login_return which will be the same tuple returned from this login function.
        :param cb_args: Extra args for success_callback
        :param cb_kwargs: Extra keyword args for success_callback

        :returns: 3 element tuple containing the a User class if one was created, response from the firebase calls, and/or any errors
        """
        if not isinstance(form_location, DeltaGenerator) and form_location != st:
            raise ValueError(
                "Location must be a streamlit DeltaGenerator (st container object such as st.sidebar) or the global st module."
            )

        res = None
        user = None
        error = None

        if cb_args is None:
            cb_args = ()
        if cb_kwargs is None:
            cb_kwargs = {}

        auth_status = self.auth_status
        if not auth_status:
            login_form = form_location.form("Login")
            login_form.subheader(form_name)

            if st.session_state["login_message"]:
                if isinstance(st.session_state["login_message"], Exception):
                    login_form.error(st.session_state["login_message"])
                else:
                    login_form.info(st.session_state["login_message"])
                st.session_state["login_message"] = None

            email = login_form.text_input("Email").lower()
            password = login_form.text_input("Password", type="password")

            if login_form.form_submit_button("Login"):
                if len(email) == 0:
                    error = LoginError("Please enter an email")
                elif len(password) == 0:
                    error = LoginError("Please enter a password")
                else:
                    res, error, login_data, validated = self._check_credentials(
                        email, password
                    )
                    if validated and login_data:
                        user, error = self._create_session(login_data)

                    if (
                        user
                        and not error
                        and success_callback
                        and callable(success_callback)
                    ):
                        success_callback(
                            *cb_args,
                            login_return=(
                                user,
                                res,
                                error,
                            ),
                            **cb_kwargs,
                        )

            login_form.form_submit_button(
                "Register", on_click=self.set_form, args=("register",)
            )
            login_form.form_submit_button(
                "Forgot password?", on_click=self.set_form, args=("reset_password",)
            )

        return (user, res, error)

    def register_user(
        self,
        form_name: str,
        form_location: Union[DeltaGenerator, ModuleType] = st,
        terms_link: Optional[str] = None,
    ) -> Tuple[Optional[dict], Optional[RegisterError]]:
        """
        Creates a user registration widget

        :param str form_name: The rendered name of the password reset form.
        :param Union[DeltaGenerator, ModuleType] form_location: The streamlit container to place the form. Either global `st` or a st container object such as st.sidebar.

        :returns: tuple containing the firebase response and any errors
        """
        if not isinstance(form_location, DeltaGenerator) and form_location != st:
            raise ValueError(
                "Location must be a streamlit DeltaGenerator (st container object such as st.sidebar) or the global st module."
            )

        register_user_form = form_location.form("Register user")
        register_user_form.subheader(form_name)
        new_email = register_user_form.text_input("Email")
        new_name = register_user_form.text_input("Name")
        new_password = register_user_form.text_input("Password", type="password")
        new_password_repeat = register_user_form.text_input(
            "Repeat password", type="password"
        )

        if terms_link is not None:
            terms_agreed = register_user_form.checkbox(
                f"By registering I agree to the terms and conditions [here]({terms_link}).",
            )
        else:
            terms_agreed = True

        user = None
        error = None
        if register_user_form.form_submit_button("Register"):
            if not terms_agreed:
                error = RegisterError(
                    "Please read and agree to the usage terms and conditions."
                )
            elif len(new_email) > 0 and len(new_name) > 0 and len(new_password) > 0:
                if new_password == new_password_repeat:
                    register_errors = {
                        "INVALID_EMAIL": "Invalid email format",
                        "EMAIL_EXISTS": "Email is already registered",
                        "WEAK_PASSWORD": "",
                    }
                    user, error = handle_firebase_action(
                        auth.create_user_with_email_and_password,
                        RegisterError,
                        register_errors,
                        new_email,
                        new_password,
                    )
                    # user = service_auth.create_user(
                    # email='user@example.com',
                    # email_verified=False,
                    # phone_number='+15555550100',
                    # password='secretPassword',
                    # display_name='John Doe',
                    # photo_url='http://www.example.com/12345678/photo.png',
                    # disabled=False)

                    if not error:
                        res1, error = handle_firebase_action(
                            auth.update_profile,
                            RegisterError,
                            False,
                            user["idToken"],
                            display_name=new_name,
                        )

                    if not error:
                        res2, error = handle_firebase_action(
                            auth.send_email_verification,
                            RegisterError,
                            False,
                            user["idToken"],
                        )
                else:
                    error = RegisterError("Passwords do not match")
            else:
                error = RegisterError(
                    "Please enter an email, username, name, and password"
                )

        register_user_form.form_submit_button(
            "Cancel", on_click=self.set_form, args=(None,)
        )

        if user and self.require_email_verification:
            verify_msg = """<p style="padding: 14px;">Registration successful. Please verify your email address, then you can <a href="/" target="_self">log in.</a></p>"""
            register_user_form.markdown(
                custom_html.custom_el(verify_msg, classes=custom_html.st_info_classes),
                unsafe_allow_html=True,
            )

        return (user, error)

    def reset_password(
        self, form_name: str, form_location: Union[DeltaGenerator, ModuleType] = st
    ) -> Tuple[Optional[dict], Optional[ResetError]]:
        """
        Creates a reset password via email widget.

        :param str form_name: The rendered name of the reset password form.
        :param Union[DeltaGenerator, ModuleType] form_location: The streamlit container to place the form. Either global `st` or a st container object such as st.sidebar.

        :returns: tuple containing the firebase response and any errors
        """
        if not isinstance(form_location, DeltaGenerator) and form_location != st:
            raise ValueError(
                "Location must be a streamlit DeltaGenerator (st container object such as st.sidebar) or the global st module."
            )

        reset_password_form = form_location.form("Reset password")
        reset_password_form.subheader(form_name)
        email = reset_password_form.text_input("Email").lower()

        res = None
        error = None
        if reset_password_form.form_submit_button("Submit"):
            if len(email) > 0:
                reset_errors = {
                    "EMAIL_NOT_FOUND": "Email address is not registered",
                    "INVALID_EMAIL": "Invalid email format",
                }
                res, error = handle_firebase_action(
                    auth.send_password_reset_email, ResetError, reset_errors, email
                )
            else:
                error = ResetError("Please enter an email")

        reset_password_form.form_submit_button(
            "Cancel", on_click=self.set_form, args=(None,)
        )

        return (res, error)

    def __repr__(self) -> str:
        return repr_(
            self,
            [
                "cookie_key",
                "service_credentials",
                "auth",
                "storage",
                "firebase_service",
            ],
        )


# @st.cache(allow_output_mutation=True, show_spinner=False, hash_funcs={"_thread.RLock": lambda _: None, "weakref.ReferenceType": lambda _: None})
def get_auth(
    cookie_name: str,
    user_class: Optional[UserInherited] = None,
    authenticator_name="authenticator",
    **kwargs,
) -> Authenticator:
    """
    See Authenticator for params.
    """
    if authenticator_name in st.session_state and st.session_state[authenticator_name]:
        return st.session_state[authenticator_name]

    cookie_key = st.secrets["authenticator"]["cookie_key"]
    admin_ids = st.secrets["authenticator"]["admin_ids"]
    developer_ids = st.secrets["authenticator"]["developer_ids"]
    return Authenticator(
        cookie_name,
        cookie_key,
        authenticator_name=authenticator_name,
        user_class=user_class,
        admin_ids=admin_ids,
        developer_ids=developer_ids,
        **kwargs,
    )
