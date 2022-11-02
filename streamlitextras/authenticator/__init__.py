import jwt
import pytz
import dateutil.parser
from types import ModuleType
from typing import Union, Optional, Tuple, TypeVar, Type, Callable
from datetime import datetime, timedelta

import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from streamlitextras.logger import log
from streamlitextras.utils import repr_
from streamlitextras.authenticator.user import User
from streamlitextras.authenticator.exceptions import AuthException, LoginError, RegisterError, ResetError, UpdateError
from streamlitextras.authenticator.utils import handle_firebase_action
from streamlitextras.webutils import get_user_timezone
from streamlitextras.cookiemanager import get_cookie_manager

import json
import requests
import pyrebase
import firebase_admin
from firebase_admin import auth as service_auth
from streamlitextras.helpers import custom_html

config = st.secrets["firebase"]
pyrebase_service = pyrebase.initialize_app(config)
auth = pyrebase_service.auth()
db = pyrebase_service.database()
storage = pyrebase_service.storage()

# PyPI doesn't contain the latest git commits for pyrebase4
def update_profile(id_token, display_name = None, photo_url=None, delete_attribute = None, *args):
    """
    Pyrebase on PyPI seems to be missing latest commits - adding this in here.
    https://firebase.google.com/docs/reference/rest/auth#section-update-profile
    """
    request_ref = "https://identitytoolkit.googleapis.com/v1/accounts:update?key={0}".format(auth.api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token, "displayName": display_name, "photoURL": photo_url, "deleteAttribute": delete_attribute, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    pyrebase.pyrebase.raise_detailed_error(request_object)
    return request_object.json()
auth.update_profile = update_profile

UserInherited = TypeVar('UserInherited', bound='User', covariant=True)
class Authenticator:
    """
    Authenticator is used to handle firebase authentication,
    as well as create streamlit widgest for login, registration,
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
    """
    def __init__(self,
                cookie_name: str,
                cookie_key: str,
                session_expiry_seconds: int = 3600 * 14,
                session_name: str = "user",
                authenticator_name: str = "authenticator",
                user_class: Optional[Type[UserInherited]] = None,
                admin_ids: Optional[Union[list, str]] = None,
                developer_ids: Optional[Union[list, str]] = None):

        if authenticator_name == session_name:
            raise ValueError("authenticator_name can't be the same as session_name (st.session_state conflict)")

        if not user_class:
            user_class = User

        self.cookie_name = cookie_name
        self.session_name = session_name
        self.session_expiry_seconds = session_expiry_seconds
        self.authenticator_name = authenticator_name
        self.cookie_key = cookie_key
        self.last_user = None
        self.user_class = user_class

        self.storage = storage
        self.auth = auth
        self.db = db

        if not admin_ids:
            admin_ids = []
        if type(admin_ids) not in [str, list]:
            raise ValueError("admin_ids must be a list or a | seperated string")
        self.admin_ids = admin_ids.split("|") if type(admin_ids) == str else admin_ids

        if not developer_ids:
            developer_ids = []
        if type(developer_ids) not in [str, list]:
            raise ValueError("developer_ids must be a list or a | seperated string")
        self.developer_ids = developer_ids.split("|") if type(developer_ids) == str else developer_ids

        # Streamlit refreshes a lot recreating this class - keep the same form between refreshes
        self.current_form = None
        if self.authenticator_name in st.session_state and st.session_state[self.authenticator_name] and st.session_state[self.authenticator_name].current_form:
            self.current_form = st.session_state[self.authenticator_name].current_form

        self.service_credentials = firebase_admin.credentials.Certificate(st.secrets["gcp_service_account"])
        try:
            self.firebase_service = firebase_admin.get_app()
        except ValueError as e:
            self.firebase_service = firebase_admin.initialize_app(self.service_credentials)

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
        if self.authenticator_name not in st.session_state or not st.session_state[self.authenticator_name]:
            st.session_state[self.authenticator_name] = self
        st.session_state[self.authenticator_name] = self

        if not self.user_tz:
            self.user_tz = get_user_timezone(default_tz="Australia/Sydney")

        # if not self.cookie_manager:
        self.cookie_manager.delayed_init()

    @property
    def auth_cookie(self) -> Optional[str]:
        """
        Gets the auth cookie

        :returns: Returns the auth cookie or None if it doesnt exist
        """
        cookie = self.cookie_manager.get(self.cookie_name)
        return cookie

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

        if self.current_user and st.session_state[self.session_name] and st.session_state["authentication_token"]:
            return True

        status, error, token_decoded = self._check_cookie()
        # log.info(f"Checked cookie for auth_status: {status} {error}")
        if error:
            if error.firebase_error:
                log.error(error)
                self._revoke_auth(error)
            return False

        if status:
            user = st.session_state[self.session_name]
            expiry_timestamp = datetime.fromtimestamp(float(token_decoded["exp_date"]), tz=pytz.UTC).timestamp()
            expires_in_seconds = expiry_timestamp - datetime.now(pytz.UTC).timestamp()
            log.success(f"""{expires_in_seconds / 3600} hours left in session cookie for {user.email}""")
            self.set_form(None)
        else:
            if not self.current_form:
                self.set_form("login")

        return status

    @property
    def current_user(self) -> Optional[UserInherited]:
        """
        Returns a User interface class instance if there is an active login
        """
        current_user = None
        if self.last_user:
            current_user = self.last_user
        elif self.session_name in st.session_state and st.session_state[self.session_name]:
            current_user = st.session_state[self.session_name]
        # else:
        #     status, error, token_decoded = self._check_cookie()
        #     if status == True:
        #         return self.current_user

        self.last_user = current_user
        return current_user

    def _create_session(self, firebase_data: dict, expiry_date: Optional[Union[datetime, int, str, float]] = None):
        """
        Creates a User from firebase token data and instantiates a session for them.

        :param dict firebase_data: The firebase data to construct the User for the session from
        :param Optional[datetime, int, str, time] expiry_date:
            an expiry datetime or timestamp (in UTC) for the session, defaults to now + self.session_expiry_seconds
        """
        if not expiry_date:
            expiry_date = (datetime.now(pytz.UTC) + timedelta(seconds=self.session_expiry_seconds))

        if type(expiry_date) is not datetime:
            expiry_date = datetime.fromtimestamp(expiry_date, tz=pytz.UTC)

        user = self.user_class(self, **firebase_data)
        self.last_user = user
        token_expiry_time = expiry_date.astimezone(tz=pytz.UTC)
        cookie_expiry_time = expiry_date.astimezone(tz=pytz.timezone(self.user_tz))
        # token_expiry_time_delta = cookie_expiry_time.timestamp() - datetime.now(pytz.UTC).timestamp()
        # session_cookie = service_auth.create_session_cookie(user.idToken, expires_in=token_expiry_time_delta)
        token = self._token_encode(user, token_expiry_time)
        st.session_state["authentication_token"] = token
        st.session_state[self.session_name] = user
        self.cookie_manager.set(self.cookie_name, token, expires_at=cookie_expiry_time)
        log.success(f"Created session {user}")

        return user

    def _token_encode(self, user: UserInherited, expiry_date: Optional[datetime] = None) -> str:
        """
        Encodes the contents of the reauthentication cookie from the auth session state

        :param UserInherited user_class: inherited User class to create the token from
        :param Optional[datetime] expiry_date: an expiry date (stored as UTC) metadata to be placed alongside the token contents, defaults to now + self.session_expiry_seconds

        :returns str: The JWT cookie for passwordless reauthentication.
        """
        if not expiry_date:
            expiry_date = (datetime.now(pytz.UTC) + timedelta(seconds=self.session_expiry_seconds))
        token_expiry_timestamp = expiry_date.timestamp()
        token = jwt.encode({self.session_name: user.firebase_data, "exp_date": token_expiry_timestamp}, self.cookie_key, algorithm="HS256")
        if not token:
            raise Exception("Token incorrectly generated")
        return token

    def _token_decode(self) -> Optional[str]:
        """
        Decodes the contents of the reauthentication cookie.

        :returns Optional[str]:
            The decoded JWT cookie for passwordless reauthentication.
            Returns None if there was an error decoding the cookie or it doesn't exist
        """
        try:
            return jwt.decode(st.session_state["authentication_token"], self.cookie_key, algorithms=["HS256"])
        except Exception as e:
            pass
            # log.warning(f"""Session token decode failure {st.session_state["authentication_token"]}""")

        try:
            auth_cookie = self.auth_cookie
            # log.warning(f"Got auth cookie: {str(auth_cookie)[:50]}")
            return jwt.decode(auth_cookie, self.cookie_key, algorithms=["HS256"])
        except Exception as e:
            pass
            # log.warning(f"Cookie token decode failure {auth_cookie}")

        return None

    @property
    def service_auth(self) -> Optional[ModuleType]:
        user = self.current_user
        if not user or not user.is_admin:
            return None
        else:
            return service_auth

    def _revoke_auth(self, error: Optional[AuthException] = None, disabled: bool = False) -> bool:
        """
        Deletes the auth cookie and revokes the firebase token it contains

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
        if self.last_user and (not error or (error and error.firebase_error != "TOKEN_EXPIRED")):
            service_auth.revoke_refresh_tokens(self.last_user.localId)
            log.info(f"Firebase tokens revoked for {self.last_user.localId}")

        # Delete cookie and reset vars
        self.last_user = None
        st.session_state[self.session_name] = None
        st.session_state["authentication_token"] = None
        self.set_form("login")
        self.cookie_manager.delete(self.cookie_name)

        return False

    def _check_cookie(self, attempt: int = 0) -> tuple[bool, AuthException, dict]:
        """
        Looks for a cookie named self.cookie_name and checks its validity
        If it is valid, loads it into the authentication session state

        :param int attempt: used internally to count circular calls of this function

        :returns tuple[bool, AuthException, dict]:
            Returns a 3 element tuple with the authentication status, any exceptions, and the decoded JWT cookie/session token if there was one
            Authentication status is True if a valid login cookie was found and login successful, else False (from _revoke_auth())
        """
        status = None
        error = None

        token_decoded = self._token_decode()
        if not token_decoded:
            error = AuthException("Error decoding JWT in cookie")
            return (False, error, token_decoded)
        if token_decoded["exp_date"] < datetime.now(pytz.UTC).timestamp():
            error = AuthException("JWT in cookie is expired")
            return (self._revoke_auth(error), error, token_decoded)
        if self.session_name not in token_decoded:
            error = AuthException("Session token not found in decoded JWT cookie")
            return (self._revoke_auth(error), error, token_decoded)

        firebase_token = token_decoded[self.session_name]
        if "idToken" not in firebase_token:
            error = AuthException("No idToken in decoded cookie token")
            return (self._revoke_auth(error), error, token_decoded)
        if "account_info" not in firebase_token:
            error = AuthException("No account_info in decoded cookie token")
            return (self._revoke_auth(error), error, token_decoded)
        if firebase_token["registered"] is False:
            error = AuthException("Account with unverified email shouldn't have cookie")
            return (self._revoke_auth(error), error, token_decoded)

        # try:
        #     decoded_claims = service_auth.verify_session_cookie(session_cookie, check_revoked=True)
        # except service_auth.InvalidSessionCookieError as e:
        #      error = e
        #      return (self._revoke_auth(error), error, token_decoded)

        # try:
        #     decoded_claims = service_auth.verify_id_token(firebase_token["idToken"], check_revoke=True)
        # except ValueError:
        #     error = e # Invalid token format
        #     return (self._revoke_auth(error), error, token_decoded)
        # except service_auth.InvalidIdTokenError as e:
        #     error = e
        #     # Refresh here
        # except service_auth.ExpiredIdTokenError as e:
        #     error = e
        #     return (self._revoke_auth(error), error, token_decoded)
        # except service_auth.RevokedIdTokenError as e:
        #     error = e
        #     return (self._revoke_auth(error), error, token_decoded)
        # except service_auth.CertificateFetchError as e:
        #     error = e
        #     return (self._revoke_auth(error), error, token_decoded)
        # except service_auth.UserDisabledError as e:
        #     error = e
        #     return (self._revoke_auth(error), error, token_decoded)
        # if datetime.now(pytz.UTC) - decoded_claims['auth_time'] < self.session_expiry_seconds:
        #     error = AuthException(f"old session id token {decoded_claims}")
        #     return (self._revoke_auth(error), error, token_decoded)

        cookie_account_info = firebase_token["account_info"]
        utcnow = datetime.now(pytz.UTC)
        valid_since_datetime = datetime.fromtimestamp(int(cookie_account_info["users"][0]["validSince"]), tz=pytz.UTC)
        valid_since_seconds = utcnow.timestamp() - valid_since_datetime.timestamp()
        last_login_datetime = datetime.fromtimestamp(float(cookie_account_info["users"][0]["lastLoginAt"][:10] + '.' + cookie_account_info["users"][0]["lastLoginAt"][-3]), tz=pytz.UTC)
        last_login_age_seconds = utcnow.timestamp() - last_login_datetime.timestamp()
        last_refresh_datetime = dateutil.parser.isoparse(cookie_account_info["users"][0]["lastRefreshAt"])
        last_refresh_age_seconds = utcnow.timestamp() - last_refresh_datetime.timestamp()
        # print("\nUTC now              ", utcnow, utcnow.timestamp())
        # print("Last log in:         ", last_login_datetime, last_login_datetime.timestamp())
        # print("Token valid since:   ", valid_since_datetime, valid_since_datetime.timestamp())
        # print("lastRefreshAt        ", cookie_account_info["users"][0]["lastRefreshAt"], last_refresh_datetime.timestamp(), last_refresh_datetime)
        # print("Token age:       ", valid_since_seconds, valid_since_seconds/3600)
        # print("Last log in age: ", last_login_age_seconds, last_login_age_seconds/3600)
        # print("lastRefreshAt    ", last_refresh_age_seconds, last_refresh_age_seconds/3600, "\n")

        if valid_since_seconds > self.session_expiry_seconds:
            error = AuthException(f"old validSince {valid_since_datetime.astimezone(pytz.timezone(self.user_tz))} {valid_since_seconds}")
            log.info(error)
            # return (self._revoke_auth(error), error, token_decoded)
        if last_login_age_seconds > self.session_expiry_seconds:
            error = AuthException(f"lastLoginAt is too old ({last_login_age_seconds}) ({last_login_datetime})")
            log.info(error)
        if last_refresh_age_seconds > self.session_expiry_seconds:
            error = AuthException(f"lastRefreshAt is too old ({last_refresh_age_seconds}) ({last_refresh_datetime})")
            return (self._revoke_auth(error), error, token_decoded)

        # Check account info and refresh the token if its expired (INVALID_ID_TOKEN)
        account_info, error = handle_firebase_action(auth.get_account_info, AuthException, False, firebase_token['idToken'])
        if error:
            error_type = error.firebase_error
            if not error_type:
                error = AuthException(f"Unknown reauth error {error}", error_type, error)
                return (self._revoke_auth(error), error, token_decoded)
            if "INVALID_ID_TOKEN" in error_type or error_type == "INVALID_ID_TOKEN":
                if attempt > 2:
                    error = AuthException("Too many authorisation attempts")
                    return (False, error, token_decoded)
                log.info(f"Session cookie token expired - refreshing {attempt}")
                refresh_errors = {"TOKEN_EXPIRED": "Too many recent sessions. Please try again later."}
                user_refresh, refresh_error = handle_firebase_action(auth.refresh, LoginError, refresh_errors, firebase_token['refreshToken'])
                if refresh_error:
                    if refresh_error.firebase_error in refresh_errors:
                        return (self._revoke_auth(refresh_error), refresh_error, token_decoded)
                    else:
                        error = AuthException(f"error refreshing token: {refresh_error.firebase_error}", refresh_error.firebase_error, refresh_error)
                        return (self._revoke_auth(error), error, token_decoded)
                else:
                    log.info("Updating refresh token")
                    firebase_token = firebase_token | user_refresh
                    self._create_session(firebase_token, token_decoded["exp_date"])
                    return self._check_cookie(attempt + 1)
            elif error_type == "TOKEN_EXPIRED":
                error = AuthException("Auth token is expired", error_type, error)
                return (self._revoke_auth(error), error, token_decoded)
            else:
                error = AuthException("Error getting account info", error_type, error)
                return (self._revoke_auth(error), error, token_decoded)

        if not error:
            status = True
            account_info["users"][0]["passwordHash"] = ""
            firebase_token["account_info"] = account_info
            self._create_session(firebase_token, token_decoded["exp_date"])

        if error:
            log.error("Failed _check_cookie()", error)

        return (status, error, token_decoded)

    def _check_credentials(self, email: str, password: str) -> Tuple[Optional[UserInherited], Optional[dict], Optional[LoginError]]:
        """
        Checks the validity of the entered credentials.

        :returns: tuple containing the User if one was created, firebase response and any errors
        """
        res = None
        user = None
        error = None
        signin_errors = {
            "INVALID_EMAIL": "Invalid email format",
            "EMAIL_NOT_FOUND": "Email address is not registered",
            "INVALID_PASSWORD": "Invalid password",
        }
        res, error = handle_firebase_action(auth.sign_in_with_email_and_password, LoginError, signin_errors, email, password)

        account_info = None
        user_refresh = None
        if not error:
            refresh_errors = {"TOKEN_EXPIRED": "Too many recent sessions. Please try again later."}
            user_refresh, error = handle_firebase_action(auth.refresh, LoginError, refresh_errors, res['refreshToken'])
            if not error:
                res = res | user_refresh

        if not error:
            account_info, error = handle_firebase_action(auth.get_account_info, LoginError, False, res['idToken'])

        if not error:
            if account_info and not account_info["users"][0]["emailVerified"]:
                error = LoginError("Please verify your email address before logging in")
                st.button("Resend verification email", on_click=self._resend_verification, args=(res["idToken"],))

        if res and not error:
            if account_info:
                account_info["users"][0]["passwordHash"] = ""
                res["account_info"] = account_info
                user = self._create_session(res)
                log.success(f"""{user.email} logged in with password""")
                if user.is_admin:
                    service_auth.set_custom_user_claims(user.localId, {'admin': True})
                    log.success(f"""Welcome {user.displayName}""")
                if user.is_developer:
                    service_auth.set_custom_user_claims(user.localId, {'devops': True})
            else:
                error = LoginError("Error retrieving account info")

        return (user, res, error)

    def _resend_verification(self, user_id_token: str) -> Tuple[Optional[dict], Optional[AuthException]]:
        """
        Resends the firebase auth verification email for a user

        :param user_id_token: The authenticated firebase auth token for the user with an unverified email address

        :returns: tuple containing the firebase response and any errors
        """
        res = None
        error = None
        resend_errors = {"TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts, try again later."}
        res, error = handle_firebase_action(auth.send_email_verification, AuthException, resend_errors, user_id_token)

        if error:
            # st.error(error)
            st.session_state["login_message"] = error
        else:
            # st.info("Verification email sent")
            st.session_state["login_message"] = "Verification email sent, please check your inbox."

        return (res, error)

    def set_form(self, form_name: Optional[str]) -> None:
        """
        Sets a variable to keep track of which form is currently displayed.

        "login" = Login form
        "register" = Registration form
        "reset_password" = Reset password form
        """
        self.current_form = form_name

    def logout(self, button_name: str, button_location: Union[DeltaGenerator, ModuleType] = st.sidebar, disabled: bool = False) -> bool:
        """
        Creates a logout button.

        :param str button_name: The rendered name of the logout button.
        :param Union[DeltaGenerator, ModuleType] button_location: The streamlit container to place the button. Either global `st` or a st container object such as st.sidebar.
        :param bool disabled: Passed to the streamlit button disabled kwarg, to optional disable the button in some circumstances. Default is False.

        :returns bool: Returns True when clicked
        """

        if not isinstance(button_location, DeltaGenerator) and button_location != st:
            raise ValueError("Location must be a streamlit DeltaGenerator (st container object such as st.sidebar) or the global st module.")

        if button_location.button(button_name, disabled=disabled, on_click=self._revoke_auth, args=(AuthException("Logout requested"), disabled,)):
            return True

        return False

    def login(self, form_name: str,
              form_location: Union[DeltaGenerator, ModuleType] = st,
              success_callback: Optional[Callable] = None,
              cb_args: Optional[tuple] = None,
              cb_kwargs: Optional[dict] = None) -> Tuple[Optional[UserInherited], dict, Optional[LoginError]]:
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
            raise ValueError("Location must be a streamlit DeltaGenerator (st container object such as st.sidebar) or the global st module.")

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
                    user, res, error = self._check_credentials(email, password)
                    if user and not error and success_callback and callable(success_callback):
                        success_callback(*cb_args, login_return=(user, res, error,), **cb_kwargs)

            login_form.form_submit_button("Register", on_click=self.set_form, args=("register",))
            login_form.form_submit_button("Forgot password?", on_click=self.set_form, args=("reset_password",))

        return (user, res, error)

    def register_user(self, form_name: str, form_location: Union[DeltaGenerator, ModuleType] = st) -> Tuple[Optional[dict], Optional[RegisterError]]:
        """
        Creates a user registration widget

        :param str form_name: The rendered name of the password reset form.
        :param Union[DeltaGenerator, ModuleType] form_location: The streamlit container to place the form. Either global `st` or a st container object such as st.sidebar.

        :returns: tuple containing the firebase response and any errors
        """
        if not isinstance(form_location, DeltaGenerator) and form_location != st:
            raise ValueError("Location must be a streamlit DeltaGenerator (st container object such as st.sidebar) or the global st module.")

        register_user_form = form_location.form("Register user")
        register_user_form.subheader(form_name)
        new_email = register_user_form.text_input("Email")
        new_name = register_user_form.text_input("Name")
        new_password = register_user_form.text_input("Password", type="password")
        new_password_repeat = register_user_form.text_input("Repeat password", type="password")

        user = None
        error = None
        if register_user_form.form_submit_button("Register"):
            if len(new_email) > 0 and len(new_name) > 0 and len(new_password) > 0:
                if new_password == new_password_repeat:
                    register_errors = {
                        "INVALID_EMAIL": "Invalid email format",
                        "EMAIL_EXISTS": "Email is already registered",
                        "WEAK_PASSWORD": "",
                    }
                    user, error = handle_firebase_action(auth.create_user_with_email_and_password, RegisterError, register_errors, new_email, new_password)

                    if not error:
                        res1, error = handle_firebase_action(auth.update_profile, RegisterError, False, user["idToken"], display_name=new_name)

                    if not error:
                        res2, error = handle_firebase_action(auth.send_email_verification, RegisterError, False, user["idToken"])
                else:
                    error = RegisterError("Passwords do not match")
            else:
                error = RegisterError("Please enter an email, username, name, and password")

        register_user_form.form_submit_button("Cancel", on_click=self.set_form, args=(None,))

        if user:
            verify_msg = """<p style="padding: 14px;">Registration successful. Please verify your email address, then you can <a href="/" target="_self">log in.</a></p>"""
            st.markdown(custom_html.custom_el(verify_msg, classes=custom_html.st_info_classes), unsafe_allow_html=True)

        return (user, error)

    def reset_password(self, form_name: str, form_location: Union[DeltaGenerator, ModuleType] = st) -> Tuple[Optional[dict], Optional[ResetError]]:
        """
        Creates a reset password via email widget.

        :param str form_name: The rendered name of the reset password form.
        :param Union[DeltaGenerator, ModuleType] form_location: The streamlit container to place the form. Either global `st` or a st container object such as st.sidebar.

        :returns: tuple containing the firebase response and any errors
        """
        if not isinstance(form_location, DeltaGenerator) and form_location != st:
            raise ValueError("Location must be a streamlit DeltaGenerator (st container object such as st.sidebar) or the global st module.")

        reset_password_form = form_location.form("Reset password")
        reset_password_form.subheader(form_name)
        email = reset_password_form.text_input("Email").lower()

        res = None
        error = None
        if reset_password_form.form_submit_button("Submit"):
            if len(email) > 0:
                reset_errors = {
                    "EMAIL_NOT_FOUND": "Email address is not registered",
                    "INVALID_EMAIL": "Invalid email format"
                }
                res, error = handle_firebase_action(auth.send_password_reset_email, ResetError, reset_errors, email)
            else:
                error = ResetError("Please enter an email")

        reset_password_form.form_submit_button("Cancel", on_click=self.set_form, args=(None,))

        if res:
            st.info("Password reset email has been sent")

        return (res, error)

    def __repr__(self) -> str:
        return repr_(self, ["cookie_key", "service_credentials", "auth", "storage", "firebase_service"])

# @st.cache(allow_output_mutation=True, show_spinner=False, hash_funcs={"_thread.RLock": lambda _: None, "weakref.ReferenceType": lambda _: None})
def get_auth(cookie_name: str, user_class: Optional[UserInherited] = None, authenticator_name = "authenticator") -> Authenticator:
    """
    See Authenticator for params.
    """
    if authenticator_name in st.session_state and st.session_state[authenticator_name]:
        return st.session_state[authenticator_name]

    cookie_key = st.secrets["authenticator"]["cookie_key"]
    admin_ids = st.secrets["authenticator"]["admin_ids"]
    developer_ids = st.secrets["authenticator"]["developer_ids"]
    return Authenticator(cookie_name,
                        cookie_key,
                        authenticator_name=authenticator_name,
                        user_class=user_class,
                        admin_ids=admin_ids,
                        developer_ids=developer_ids)
