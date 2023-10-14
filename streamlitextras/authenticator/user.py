from streamlitextras.logger import log
from streamlitextras.utils import repr_
from streamlitextras.authenticator.utils import handle_firebase_action
from streamlitextras.authenticator.exceptions import (
    AuthException,
    LoginError,
    RegisterError,
    ResetError,
    UpdateError,
)


class User:
    """
    This class is used as an interface for Authenticators users
    """

    def __init__(self, authenticator, auth_data, login_data={}, debug: bool = False):
        """
        Initializes a user account with associated firebase tokens and account information

        :param Authenticator authenticator: The associated Authenticator class that spawned this user
        :param dict auth_data:
            Dict containing session_cookie, decoded_claims and user_record
        :param dict login_data:
            The data from the initial login, not always provided (when reading session cookies)
        """
        self.debug = debug

        self.authenticator = authenticator
        self.auth_data = auth_data
        self.login_data = login_data

        self.idToken = login_data.get("idToken", None)
        self.expiresIn = login_data.get("expiresIn", None)
        self.registered = login_data.get("registered", None)
        self.refreshToken = login_data.get("refreshToken", None)

        self.user_record = auth_data["user_record"]
        self.session_cookie = auth_data["session_cookie"]
        self.decoded_claims = auth_data["decoded_claims"]

        self.uid = self.decoded_claims["uid"]
        self.localId = self.user_record["localId"]

        self.email = self.user_record["email"]
        self.emailVerified = self.user_record["emailVerified"]
        self.displayName = self.user_record.get("displayName", None)
        self.createdAt = self.user_record.get("createdAt", None)
        self.lastLoginAt = self.user_record.get("lastLoginAt", None)
        self.lastRefreshAt = self.user_record.get("lastRefreshAt", None)
        self.passwordUpdatedAt = self.user_record.get("passwordUpdatedAt", None)
        self.providerUserInfo = self.user_record.get("providerUserInfo", None)
        self.validSince = self.user_record.get("validSince", None)
        self.photoUrl = self.user_record.get("photoUrl", None)

        self.account_info = login_data.get("account_info", None)
        self.users = self.account_info["users"] if self.account_info else None
        self.user = self.users[0] if self.users else None
        self.disabled = self.user.get("disabled", None) if self.user else None
        self.customAuth = self.user.get("customAuth", None) if self.user else None

    def refresh_token(self):
        refreshed = None
        refresh_errors = {
            "TOKEN_EXPIRED": "Too many recent sessions. Please try again later."
        }
        user_refresh, refresh_error = handle_firebase_action(
            self.authenticator.auth.refresh,
            LoginError,
            refresh_errors,
            self.refreshToken,
        )
        if not refresh_error:
            self.login_data = {**self.login_data, **user_refresh}
            for key in self.__dict__.keys():
                if key in user_refresh and hasattr(self, key):
                    setattr(self, key, user_refresh[key])
            self.authenticator._create_session(self.login_data)
            refreshed = True
            if self.debug:
                log.info(f"Users tokens refreshed {self.uid}.")
        else:
            log.error(f"Error refreshing users firebase token {refresh_error}")
            refreshed = False

        return refreshed

    @property
    def firebase_user(self):
        """
        Gets the UserRecord object from the official firebase python SDK

        # https://firebase.google.com/docs/reference/admin/python/firebase_admin.auth#firebase_admin.auth.UserRecord
        """
        self.authenticator.service_auth.get_user(self.uid)

    @property
    def is_admin(self):
        """
        Returns true if users firebase id is in self.authenticator.admin_ids
        """
        admin_ids = self.authenticator.admin_ids
        return self.localId in admin_ids

    @property
    def is_developer(self):
        """
        Returns true if users firebase id is in self.authenticator.developer_ids
        """
        developer_ids = self.authenticator.developer_ids
        return self.localId in developer_ids

    def __repr__(self) -> str:
        return repr_(
            self,
            ["passwordHash", "login_data", "refreshToken", "idToken", "authenticator"],
            only_keys=["localId", "email"],
        )
