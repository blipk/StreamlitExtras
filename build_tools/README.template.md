# Streamlit Extras

These are some components and modules designed to make working with streamlit easier.

I had a project that required some of these parts, I tried some other community projects that were similar,
but none of them had the features I required, so I ended up rewriting my own implementations of them.

## Installation and Requirements

Install from PyPI with pip:
`python3 -m pip install streamlit-base-extras`

Requires Streamlit 1.13.0+ and Python 3.9+,
will consider releasing versions compatible with older Python3 if people show interest.

Some helper functions require `streamlit-javascript` too.

## The modules

#### Cookie Manager
Component function to manage in-browser cookies from streamlit.

@@COOKIEMANAGER

#### Router
Page router with various features.

@@ROUTER

#### Authenticator
Authentication module that creates streamlit register/login forms, and uses firebase auth to register and manage users.
Can also be inherited to use a custom authentication provider.

@@AUTHENTICATOR

#### Threader
Makes spawning and working with `threading.Threads` with streamlit easy.

@@THREADER

#### Logger
Implementation of Loguru set up to work well with this package.

@@LOGGER

#### Misc
See the [API docs](https://streamlitextras.readthedocs.io/en/latest/api.html) for a full list of functions and their usage in these files.

##### webutils.py
Some utility functions to run javascript, wrappers around various javascript routines,
and some other browser related formatting utilities.

##### helpers.py
Class implementation that streamlines creating basic HTML elements with st.markdown,
and some other useful functions.

##### storageservice.py
Helper to interact with Google Cloud Storage with a service worker account.

##### utils.py
Some utility functions for Python development.
