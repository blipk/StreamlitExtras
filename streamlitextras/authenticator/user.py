from streamlitextras.logger import log
from streamlitextras.utils import repr_
from streamlitextras.authenticator.utils import handle_firebase_action
from streamlitextras.authenticator.exceptions import AuthException, LoginError, RegisterError, ResetError, UpdateError

class User:
    """
    This class is used as an interface for Authenticators users
    """
    def __init__(self, authenticator, **kwargs):
        """
        Initializes a user account with associated firebase tokens and account information

        :param Authenticator authenticator: The associated Authenticator class that spawned this user
        :param dict **kwargs: The data associated with this class, the firebase_data from firebase APIs if Authenticator hasn't been inherited
        """
        firebase_data = kwargs
        self.authenticator = authenticator
        self.firebase_data = firebase_data
        # Sign in
        self.localId = firebase_data["localId"]
        self.uid = firebase_data["localId"]
        self.email = firebase_data["email"]
        self.idToken = firebase_data["idToken"]
        self.expiresIn = firebase_data["expiresIn"] # idToken
        self.registered = firebase_data["registered"]
        self.refreshToken = firebase_data["refreshToken"]
        self.displayName = firebase_data["displayName"]

        self.account_info = firebase_data["account_info"]
        self.users = firebase_data["account_info"]["users"]
        self.user = self.users[0] # Only supporting single identify provider - password
        # Already provided: localId, email, displayName, passwordHash
        self.emailVerified = self.user["emailVerified"]
        self.passwordUpdatedAt = self.user["passwordUpdatedAt"]
        self.providerUserInfo = self.user["providerUserInfo"]  # Only used if using federated SSO etc
        self.photoUrl = self.user["photoUrl"] if "photoUrl" in self.user else None
        self.validSince = self.user["validSince"] # The timestamp, in seconds, which marks a boundary, before which Firebase ID token are considered revoked.
        self.disabled = self.user["disabled"] if "disabled" in self.user else None
        self.lastLoginAt = self.user["lastLoginAt"]
        self.createdAt = self.user["createdAt"]
        self.lastRefreshAt = self.user["lastRefreshAt"]
        self.customAuth = self.user["customAuth"] if "customAuth" in self.user else None

    def refresh_token(self):
        refreshed = None
        refresh_errors = {"TOKEN_EXPIRED": "Too many recent sessions. Please try again later."}
        user_refresh, refresh_error = handle_firebase_action(self.authenticator.auth.refresh, LoginError, refresh_errors, self.refreshToken)
        if not refresh_error:
            self.firebase_data = self.firebase_data | user_refresh
            for key in self.__dict__.keys():
                if key in user_refresh and hasattr(self, key):
                    setattr(self, key, user_refresh[key])
            self.authenticator._create_session(self.firebase_data)
            refreshed = True
            log.info("Users tokens refreshed.")
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
        return repr_(self, ["passwordHash", "firebase_data", "refreshToken", "idToken", "authenticator"], only_keys=["localId", "email"])
