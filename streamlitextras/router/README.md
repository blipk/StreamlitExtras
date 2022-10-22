# Streamlit Extras Router

Router is a class to manage pages and routing to them, either via browser query strings or via other paths in your code.

#### Basic usage

Note that `st.set_page_config` must be called before getting the router.

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

This will set the browser query string to `/?page_name=page_state` and render the page function associated with that page name in pages.

`router.route()` takes the key from the `pages` dict as the first argument, and routes to that page, with no arguments will default to the first page in `pages`

Due to a streamlit bug not being able to read empty query strings, page_state will show as `~` in the browser URL if there is none.

Instead of using `router.route()` you can use `router.show_route_view()` which will bypass setting query strings and just run that page function:

```Python
computed_chance = random.randrange(10)
if computed_chance > 1:
    router.show_route_view()
else:
    router.show_route_view("other", computed_chance)
```

See the API docs for more usage options, such as setting a callable pre-route function, or passing extra page_state/dependencies to every page_function.

#### Advanced usage

Below is an implementation that uses a routes folder module to manage pages.

routes folder `__init__.py`
```Python
import streamlitextras

router: streamlitextras.router.Router
auth: streamlitextras.authenticator.Authenticator
cookie_manager: streamlitextras.cookiemanager.CookieManager

def __getattr__(name):
    if name == "cookie_manager":
        cookie_manager = streamlitextras.cookiemanager.get_cookie_manager()
        return cookie_manager
    elif name == "auth":
        auth = streamlitextras.authenticator.get_auth("my_cookie")
        return auth
    elif name == "router":
        router = streamlitextras.router.get_router(pages, pre_route)
        return router
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

from .preroute import pre_route
from .userpage import user_page
from .authpage import auth_page
from .mainpage import main_page

pages = {
    "main": main_page,
    "user": user_page,
    "auth": auth_page,
}

```

`main.py`
```Python
import os
import streamlit as st
from streamlitextras.authenticator.exceptions import AuthException
from streamlitextras.logger import log
st.set_page_config(
    page_title="",
    layout="wide",
    initial_sidebar_state="auto"
)
import routes # NOTE: This has to be imported after st.set_page_config()


router = None
auth = None
cookie_manager = None
def main() -> None:
    router = routes.router
    auth = routes.auth
    cookie_manager = routes.cookie_manager

    # This is required to make sure current instances stay in session_state
    auth.delayed_init()
    router.delayed_init()

    try:
        auth_status = auth.auth_status
        user = auth.current_user
        log.info(f"Auth status: {auth_status} - User: {user.localId if user else user}")
    except AuthException as e:
        log.error(f"Error checking auth_status {e}")
        return router.show_route_view("auth")

    if auth_status and user:
        router.show_route_view(redirect_page_names=["auth"])
    else:
        router.show_route_view("auth")

if __name__ == "__main__":
    main()

```

For full reference see the API docs.