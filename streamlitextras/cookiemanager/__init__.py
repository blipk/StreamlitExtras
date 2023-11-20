import os
import time
import streamlit as st
import streamlit.components.v1 as components
from streamlitextras.logger import log
from streamlitextras.utils import repr_

absolute_path = os.path.dirname(os.path.abspath(__file__))
build_path = os.path.join(absolute_path, "frontend/build")
_component_func = components.declare_component("cookie_manager", path=build_path)


class CookieManager:
    """
    This is a streamlit component class to manage cookies.

    It uses a thin component instance wrapper around the universal-cookie library.
    """

    def __init__(self, debug: bool = False):
        if "cookie_manager" in st.session_state and st.session_state["cookie_manager"]:
            self.cookies = st.session_state["cookie_manager"].cookies.copy()
        else:
            self.cookies = {}
        st.session_state["cookie_manager"] = self
        self.debug = debug
        if self.debug:
            log.debug(f"Initialized Cookie Manager {hex(id(self))}")

    def delayed_init(self):
        """
        Used to delay initialization of streamlit objects so this class can be cached
        """
        st.session_state["cookie_manager"] = self

    def cookie_manager(self, *args, **kwargs):
        time.sleep(0.1)
        try:
            result = _component_func(**kwargs)
        except st.errors.DuplicateWidgetID:
            kwargs["key"] = f"""{kwargs["key"]}{time.time()}"""
            result = _component_func(**kwargs)
        time.sleep(0.1)  # This ensures we get a result before streamlit redraws
        return result

    def set(
        self,
        name,
        value,
        expires_at=None,
        secure=None,
        path=None,
        same_site=None,
        key="set",
    ):
        """
        Set a cookie with name, value and options.
        Defaults are set in the JS component and listed below

        :param name: The name of the cookie
        :param value: The value of the cookie
        :param expires_at:
            Datetime of when the cookie expires.
            Default is set in the js at 1 day from browser timezone.
        :param secure: Secure flag, default is true.
        :param path: Cookie path, default is /
        :param same_site: Same site attribute, default is "strict"

        :param key: streamlit key used for the component instance

        :returns: True if the operation was successful, else False
        """
        if name is None or name == "":
            return False

        expires_at = expires_at.isoformat() if expires_at else None
        options = {
            "name": name,
            "value": value,
            "expires": expires_at,
            "sameSite": same_site,
        }
        result = self.cookie_manager(
            method="set", options=options, key=key, default=False
        )
        if result:
            self.cookies[name] = result

        return True

    def get(self, name, key="get"):
        """
        Gets a value of a cookie.
        NOTE: The value isn't got directly from the component instance
        This class fills all cookies in self.cookies everytime streamlit instances it on the page

        Returns empty {} dict if no result. Returns None if the operation failed.

        :param name: The name of the cookie to get the value of

        :returns Union[str, dict]:
            Returns the cookie value, it may be deserialized from JSON to a dict
        """
        if not self.cookies:
            self.cookies = self.cookie_manager(method="getAll", key=key, default={})

        if name is None or name == "":
            return None
        result = self.cookies.get(name, None)
        time.sleep(0.4)  # Give component time to render
        return result

    def get_all(self, key="get_all"):
        """
        Get a dict of all the cookies in the browser, and update self.cookies

        :param key: streamlit key used for the component instance

        :returns: A dict of all the cookies
        """
        self.cookies = self.cookie_manager(method="getAll", key=key, default={})
        return self.cookies

    def delete(self, name, key="delete"):
        """
        Delete a cookie from the browser

        :param name: the name of the cookie to delete
        :param key: streamlit key used for the component instance

        :returns: True if the operation was successful, or else False
        """
        if name is None or name == "":
            return False

        result = self.cookie_manager(
            method="delete", options={"name": name}, key=key, default=False
        )
        if result and name in self.cookies:
            del self.cookies[name]
        return result

    def __repr__(self) -> str:
        return repr_(self)


# @st.cache(allow_output_mutation=True, show_spinner=False)
def get_cookie_manager() -> CookieManager:
    if "cookie_manager" in st.session_state and st.session_state["cookie_manager"]:
        return st.session_state["cookie_manager"]
    return CookieManager()
