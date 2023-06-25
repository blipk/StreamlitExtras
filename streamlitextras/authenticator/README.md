# Streamlit Extras Authenticator

Authenticator is a class to manage creating streamlit authentication forms (login/registration) and to create and manage users via firebase auth.

#### Basic usage

```Python
import streamlit as st
from streamlitextras.authenticator import get_auth

auth = None
def main():
    global auth
    auth = get_auth("my_cookie_name")
    auth.delayed_init() # This is required to make sure current Authenticator stays in session state

    auth_status = auth.auth_status
    user = auth.current_user

    if auth_status and user:
        st.write(f"Welcome {user.displayName}!")
    else:
        auth_page()

def auth_page():
    if auth.current_form == "login" or not auth.current_form:
        user, res, error = auth.login("Login")
    if auth.current_form == "register":
        res, error = auth.register_user("Register")
    elif auth.current_form == "reset_password":
        res, error = auth.reset_password("Request password change email")

    if res:
        st.info("Success!")

    if error:
        st.error(error.message)

if __name__ == "__main__":
    main()

```

You will also need to set up some secrets in .streamlit/secrets.toml, you can find the firebase details through the section at the bottom on your firebase project settings page.

```TOML
[authenticator]
cookie_key = "my_c00k!e_jwt_k3y"
admin_ids = ""
developer_ids = ""

[firebase]
apiKey = ""
authDomain = ""
projectId = ""
storageBucket = ""
messagingSenderId = ""
appId = ""
measurementId = ""
databaseURL = ""
```

###### The User

As per the example above, when a user is logged in you can access it with `auth.current_user`. The user class has two basic properties `is_admin` and `is_developer` which return True if the users firebase localId is in your config.toml admin_ids or developer_ids

It also has the function `User.refresh_token()` which will update the users firebase auth refresh token, this is done automatically in Authenticator when required, but should also be used before making any additional calls to firebase or google cloud that use the users `localId`

You will also probably want extend the User class to implement user functionality specific to your app, you can provide a reference to your own class that inherits `authenticator.User` and pass it to `get_auth("cookie_name", user_class=MyUser)`

```Python
from streamlitextras.authenticator import User

class MyUser(User):
    def __init__(self, authenticator, **kwargs):
        super().__init__(authenticator, **kwargs)

    def get_user_files():
        """Get user files or something else specific to your app"""
```

#### Advanced usage

If you want to use the streamlit integration but use a different authentication service provider, you can create your own class that inherits Authenticator and override the private methods.