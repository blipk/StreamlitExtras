import time
import streamlit as st
from urllib.parse import quote, unquote
from typing import Tuple, Optional, Callable
from streamlitextras.webutils import stxs_javascript
from streamlitextras.logger import log
from streamlitextras.utils import repr_

class Router:
    """
    Page router for streamlit.

    :param dict[str, Callable] routes:
        Dictionary mapping of routes to their page functions, in the format {page_name: page_function}
    :param Optional[Callable] preroute:
        Optional callable page function that will be executed before each active page function
    :param Optional[list] dependencies:
        Optional dict to pass as kwargs to every page_function call
    """
    def __init__(self,
                routes: dict[str, Callable],
                preroute: Optional[Callable] = None,
                dependencies: Optional[dict] = None):
        self.routes = routes
        self.preroute = preroute
        self.dependencies = dependencies
        self.page_names = list(self.routes.keys())
        log.debug(f"Initialized router {hex(id(self))}")

    def delayed_init(self):
        """
        Used to delay initialization of streamlit objects so this class can be cached
        """
        if "router" not in st.session_state or not st.session_state["router"]:
            st.session_state["router"] = self
        st.session_state["router"] = self

    @property
    def default_page(self):
        """
        Returns the default page. Currently the first in self.pages
        """
        return self.page_names[0]

    @property
    def current_page(self):
        page_name, page_state = self.current_page_data()
        return page_name

    @property
    def current_state(self):
        page_name, page_state = self.current_page_data()
        return page_state

    def current_page_data(self) -> Tuple:
        """
        Returns the current page name and page from the query string
        """
        query_params = st.experimental_get_query_params()
        page_name = None
        page_state = None

        for q_page_name, q_page_state in query_params.items():
            if q_page_name in self.page_names:
                page_state = q_page_state
                page_name = q_page_name
                break

        if not page_name:
            page_name = self.default_page

        if page_state and page_state[0] != "None":
            page_state = unquote(page_state[0])
        else:
            page_state = None

        return (page_name, page_state)

    def show_route_view(self,
                        force_page_name: Optional[str] = None,
                        args: Optional[tuple] = None,
                        kwargs: Optional[dict] = None,
                        redirect_page_names: Optional[list[str]] = None):
        """
        Checks the query params and routes to the requested page,
        or routes to force_page_name directly, not setting any query params

        :param force_page_name:
            If provided will route to this page via its function in self.routes,
            bypassing query string params.
        :param args:
            Tuple of args to pass to the page func for force_page_name
        :param kwargs:
            Dict of kwargs to pass to the page func for force_page_name
            They will take precedence over and be merged with self.dependencies
        :param redirect_page_names:
            If page name from query string is in this list, will be redirected to the default route instead.
            Useful for conditional redirection in authentication etc.
        """
        if force_page_name:
            page_name = force_page_name
        else:
            page_name, page_state = self.current_page_data()
            args = (page_state,)

        redirect = False
        if redirect_page_names and page_name in redirect_page_names:
            redirect = True
            page_name = self.default_page
            kwargs = {}
            args = ()

        page_func = self.routes[page_name]

        if type(kwargs) != dict:
            kwargs = {}

        if self.dependencies and type(self.dependencies) is dict:
            kwargs = self.dependencies | kwargs

        if args is None or args in [("",), ("~",), ("None",), "", "~", "None"]:
            args = ()

        if self.preroute and callable(self.preroute):
            # log.debug(f"Running preroute {self.preroute}")
            self.preroute()

        log.info(f"Routing to {page_name} {redirect}")
        if redirect is True:
            st.experimental_set_query_params(**{page_name: "~"})
            st.experimental_rerun()

        if callable(page_func):
            # log.debug(f"Calling page_func {page_func}")
            page_func(*args, **kwargs)

        if len(args) == 0:
            stxs_javascript(f"""window.history.pushState({{}}, "", "/?{page_name}=~");""")

    def route(self, page_name: str = None, page_state: Optional[str] = None, rerun_st: bool = False):
        """
        Routes to a page.
        First found query string matching a page key in self.routers is routed too.
        Query string value can be set to page data

        :param Optional[str] page_name:
            The key for the page in self.routes - query param key will be set the same
            If it is None first page in self.routes will be used, and no query params will be set (redirect to /)
        :param Optional[str] page_state:
            Optional string to include as page state, will be urlencoded/urldecoded
        :param bool rerun_st:
            Whether to call st.experimental_rerun() - not needed if calling this from a st callback
        """
        query_params = {}
        page_state = quote(page_state) if page_state else "~"
        if page_name:
            query_params = {page_name: page_state}
        else:
            page_name = self.default_page
            query_params = {page_name: page_state}

        log.info(f"Setting query params {query_params}")
        st.experimental_set_query_params(**query_params)
        if rerun_st is True:
            log.debug("rerun_st is True")
            time.sleep(0.1)
            st.experimental_rerun()

    def __repr__(self) -> str:
        return repr_(self, ["routes"])

router_hash_funcs = {"_thread.RLock": lambda _: None,
                    "builtins.method": lambda _: None,
                    "builtins.property": lambda _: None,
                    "builtins.function": lambda _: None,
                    "_cffi_backend.__CDataGCP": lambda _: None,
                    "google.cloud.storage.client.Client": lambda _: None,
                    "streamlit.delta_generator.DeltaGenerator": lambda _: None}

# @st.cache(allow_output_mutation=True, show_spinner=False, hash_funcs=router_hash_funcs)
def get_router(routes: dict[str, Callable], preroute: Optional[Callable] = None, dependencies: Optional[dict] = None) -> Router:
    """
    See Router for params.
    """
    if "router" in st.session_state and st.session_state["router"]:
        st.session_state["router"].routes = routes
        st.session_state["router"].preroute = preroute
        return st.session_state["router"]
    return Router(routes, preroute, dependencies)
