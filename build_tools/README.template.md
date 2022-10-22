# Streamlit Extras

These are some components and modules designed to make working with streamlit easier.

### Cookie Manager

Component function to manage in-browser cookies from streamlit.

@@COOKIEMANAGER

### Router

Page router with various features.

@@ROUTER

### Authenticator

Authentication module that creates streamlit register/login forms, and uses firebase auth to register and manage users.
Can also be inherited to use a custom authentication provider.

@@AUTHENTICATOR

### Threader

Makes spawning and working with threading.Threads with streamlit easy.

@@THREADER

### Logger

Implementation of Loguru set up to work well with this package.

@@LOGGER

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