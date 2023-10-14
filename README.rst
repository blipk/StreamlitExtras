Streamlit Extras
================

These are some components and modules designed to make working with
streamlit easier.

I had a project that required some of these parts, I tried some other
community projects that were similar, but none of them had the features
I required, so I ended up rewriting my own implementations of them.

Installation and Requirements
-----------------------------

Install from PyPI with pip:
``python3 -m pip install streamlit-base-extras``

Requires Streamlit 1.13.0+ and Python 3.9+, will consider releasing
versions compatible with older Python3 if people show interest.

Some helper functions require ``streamlit-javascript`` too.

The modules
-----------

Router
~~~~~~

Page router with various features.

.. code:: python

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

See the `package readme <streamlitextras/router>`__ or `API
docs <https://streamlitextras.readthedocs.io/en/latest/api/streamlitextras.html>`__
for more details.

Cookie Manager
~~~~~~~~~~~~~~

Component function to manage in-browser cookies from streamlit.

.. code:: python

   import streamlit as st
   from streamlitextras.cookiemanager import get_cookie_manager

   cookie_manager = None
   def main():
       global cookie_manager
       cookie_manager = get_cookie_manager()
       cookie_manager.delayed_init() # Makes sure CookieManager stays in st.session_state

       cookie_manager.set("my_cookie_name", "I'm a cookie!")
       my_cookie_value = cookie_manager.get("my_cookie_name")
       print(my_cookie_value) # "I'm a cookie"

       my_cookies = cookie_manager.get_all()
       print(my_cookies) # {"my_cookie_name": "I'm a cookie!"}

       cookie_manager.delete("my_cookie_name")
       my_cookie_value = cookie_manager.get("my_cookie_name")
       print(my_cookie_value) # None


   if __name__ == "__main__":
       main()

See the `package readme <streamlitextras/cookiemanager>`__ or `API
docs <https://streamlitextras.readthedocs.io/en/latest/api/streamlitextras.html>`__
for more details.

Authenticator
~~~~~~~~~~~~~

Authentication module that creates streamlit register/login forms, and
uses firebase auth to register and manage users. Can also be inherited
to use a custom authentication provider.

.. code:: python

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
       info_box = st.container()

       if auth.current_form == "login" or not auth.current_form:
           user, res, error = auth.login("Login")
       if auth.current_form == "register":
           res, error = auth.register_user("Register")
       elif auth.current_form == "reset_password":
           res, error = auth.reset_password("Request password change email")

       if res:
           info_box.info("Success!")

       if error:
           info_box.error(error.message)

   if __name__ == "__main__":
       main()

See the `package readme <streamlitextras/authenticator>`__ or `API
docs <https://streamlitextras.readthedocs.io/en/latest/api/streamlitextras.html>`__
for more details.

Threader
~~~~~~~~

Makes spawning and working with ``threading.Threads`` with streamlit
easy.

.. code:: python

   import time
   import streamlit as st
   import reruntrigger_default # This is required so the watcher can rerun from this file
   from streamlitextras.threader import lock, trigger_rerun, \
                                        streamlit_thread, get_thread, \
                                        last_trigger_time

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

See the `package readme <streamlitextras/threader>`__ or `API
docs <https://streamlitextras.readthedocs.io/en/latest/api/streamlitextras.html>`__
for more details.

Logger
~~~~~~

Implementation of Loguru set up to work well with this package.

.. code:: python

   import streamlit as st
   from streamlitextras.logger import log

   def main():
       log.debug("My app just started!")
       st.write("My app")

   if __name__ == "__main__":
       main()

See the `package readme <streamlitextras/logger>`__ or `API
docs <https://streamlitextras.readthedocs.io/en/latest/api/streamlitextras.html>`__
for more details.

Other helpers
~~~~~~~~~~~~~

See the `API
docs <https://streamlitextras.readthedocs.io/en/latest/api/streamlitextras.html>`__
for a full list of functions and their usage in these files.

streamlitextras.webutils
^^^^^^^^^^^^^^^^^^^^^^^^

Some utility functions to run javascript, wrappers around various
javascript routines, and some other browser related formatting
utilities.

.. code:: python

   import streamlit as st
   from streamlitextras.webutils import stxs_javascript, get_user_timezone, \
                                       bytes_to_data_uri, trigger_download

   def main():
       # Returns tz database name can be used with pytz and datetime
       timezone = get_user_timezone()
       continent, city = timezone.split("/")
       stxs_javascript(f"""alert("Hello person from {city}! Welcome to my streamlit app.");"""

       uploaded_file = st.file_uploader("Upload a file")

       if uploaded_file:
           data_uri = bytes_to_data_uri(uploaded_file)
           # Browser will prompt to save the file
           trigger_download(data_uri, "The file you just uploaded.renamed")

   if __name__ == "__main__":
       main()

See the `source code <streamlitextras/webutils.py>`__.

streamlitextras.helpers
^^^^^^^^^^^^^^^^^^^^^^^

Class implementation that streamlines creating basic HTML elements with
st.markdown, and some other useful functions.

See the `source code <streamlitextras/helpers.py>`__.

streamlitextras.storageservice
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Helper to interact with Google Cloud Storage with a service worker
account.

It has some basic wrapper functions to use the service account to manage
buckets and blobs, as well as computing hashes from Python bytes objects
that match gcloud blobs.

See the `source code <streamlitextras/storageservice.py>`__ and the
`google python api
reference <https://googleapis.dev/python/storage/latest/>`__ for more.

.. code:: python

   import streamlitextras.storageservice as storageservice

   with open("my.file", "rb") as f:
       computed_md5_hash = storageservice.compute_bytes_md5hash(f.read())

   buckets = storageservice.get_buckets() # Returns an iterable
   list_buckets = []
   for bucket in buckets:
       list_buckets.append(buckets)
   buckets = list_buckets

   blobs = get_blobs(buckets[0].name) # Returns an iterable
   list_blobs = p[]
   for blob in blobs:
       list_blobs.append(blob)
   blobs = list_blobs

   my_file_blob = blobs[0] # my.file

   assert my_file_blob.md5_hash == computed_md5_hash # True

You will need to set up a service worker on your google cloud project or
firebase project, and add the details from its .json key to
``.streamlit/secrets.toml``

.. code:: toml

   [gcp_service_account]
   type = ""
   project_id = ""
   private_key_id = ""
   private_key = ""
   client_email = ""
   client_id = ""
   auth_uri = ""
   token_uri = ""
   auth_provider_x509_cert_url = ""
   client_x509_cert_url = ""

streamlitextras.utils
^^^^^^^^^^^^^^^^^^^^^

Some utility functions for Python development.

See the `source code <streamlitextras/utils.py>`__.
