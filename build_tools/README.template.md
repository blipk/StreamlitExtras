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

#### Router
Page router with various features.

@@ROUTER

#### Cookie Manager
Component function to manage in-browser cookies from streamlit.

@@COOKIEMANAGER

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

#### Other helpers
See the [API docs](https://streamlitextras.readthedocs.io/en/latest/api/streamlitextras.html) for a full list of functions and their usage in these files.

###### streamlitextras.webutils
Some utility functions to run javascript, wrappers around various javascript routines,
and some other browser related formatting utilities.

```Python
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
```

See the [source code](streamlitextras/webutils.py).

###### streamlitextras.helpers
Class implementation that streamlines creating basic HTML elements with st.markdown,
and some other useful functions.

See the [source code](streamlitextras/helpers.py).

###### streamlitextras.storageservice
Helper to interact with Google Cloud Storage with a service worker account.

It has some basic wrapper functions to use the service account to manage buckets and blobs,
as well as computing hashes from Python bytes objects that match gcloud blobs.

See the [source code](streamlitextras/storageservice.py) and the [google python api reference](https://googleapis.dev/python/storage/latest/) for more.

```Python
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
```

You will need to set up a service worker on your google cloud project or firebase project,
and add the details from its .json key to `.streamlit/secrets.toml`

```TOML
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
```

###### streamlitextras.utils
Some utility functions for Python development.

See the [source code](streamlitextras/utils.py).
