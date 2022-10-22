# Streamlit Extras

These are some components and modules designed to make working with streamlit easier.

### Cookie Manager

Component function to manage in-browser cookies from streamlit.

```Python
import streamlit as st
from streamlitextras.cookiemanager import get_cookie_manager

cookie_manager = None
def main():
    global cookie_manager
    cookie_manager = get_cookie_manager()

    cookie_manager.set("my_cookie_name", "I'm a cookie!")
    my_cookie_value = cookie_manager.get("my_cookie_name")
    print(my_cookie_value) # "I'm a cookie"

    my_cookies = cookie_manager.get_all("my_cookie_name")
    print(my_cookies) # {"my_cookie_name": "I'm a cookie!"}

    cookie_manager.delete("my_cookie_name")
    my_cookie_value = cookie_manager.get("my_cookie_name")
    print(my_cookie_value) # None


if __name__ == "__main__":
    main()
```

See the [package readme](streamlitextras/cookiemanager) or API docs for more details.


### Router

Page router with various features.

```Python
import random
import streamlit as st
from streamlitextras.router import get_router

router = None
def main():
    global router
    pages = {
        "main": main_page,
        "other": another_page,
    }
    st.set_page_config(
        page_title="MyApp",
        layout="wide",
        initial_sidebar_state="auto"
    )
    router = get_router()
    router.delayed_init()  # This is required to make sure current Router stays in session state

    computed_chance = random.randrange(10)
    if computed_chance > 1:
        router.route()
    else:
        router.route("other", computed_chance)

def main_page(page_state = None):
    st.write("This is the main.")

def another_page(page_state = None):
    st.write(f"This is another page, you're lucky to be here. Number {page_state} lucky.")

if __name__ == "__main__":
    main()
```

See the [package readme](streamlitextras/router) or API docs for more details.


### Authenticator

Authentication module that creates streamlit register/login forms, and uses firebase auth to register and manage users.
Can also be inherited to use a custom authentication provider.

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

    if error:
        st.error(error.message)

if __name__ == "__main__":
    main()

```

See the [package readme](streamlitextras/authenticator) or API docs for more details.


### Threader

Makes spawning and working with threading.Threads with streamlit easy.

```Python
import time
import streamlit as st
from streamlitextras.threader import lock, trigger_rerun, streamlit_thread, get_thread, last_trigger_time

router = None
def main():
    thread_name = streamlit_thread(my_threaded_function, (5,))
    st.write("This should be here before my_threaded_function() is done!")
    st.button("Thread info", on_click=button_callback, args=(thread_name,))

def button_callback(thread_name):
    # Sometimes streamlit will trigger button callbacks when re-running,
    # So we block them if we triggered a rerun recently
    if last_trigger_time() < 1:
        return
    my_thread = get_thread(thread_name)
    st.write(my_thread) # threading.Thread

def my_threaded_function(time):
    time.sleep(time)
    with lock:
        # Do something that might interfere with other threads,
        # file operations or setting st.session_state
        pass
    print(f"Thread done! I slept for {time} seconds.")

if __name__ == "__main__":
    main()
```

See the [package readme](streamlitextras/threader) or API docs for more details.


### Logger

Implementation of Loguru set up to work well with this package.

```Python
import streamlit as st
from streamlitextras.logger import log

def main():
    log.debug("My app just started!")
    st.write("My app")

if __name__ == "__main__":
    main()
```

See the [package readme](streamlitextras/logger) or API docs for more details.


### Misc

See the API docs for a full list of functions and their usage in these files.

#### webutils.py

Some utility functions to run javascript, wrappers around various javascript routines,
and some other browser related formatting utilities.

#### helpers.py

Class implementation that streamlines creating basic HTML elements with st.markdown

#### storageservice.py

Helper to interact with Google Cloud Storage with a service worker account.

#### utils.py

Some utility functions for Python development.