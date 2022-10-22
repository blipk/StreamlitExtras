# Streamlit Extras Cookie Manager

Cookie Manager is a streamlit component function that uses the npm library universal-cookie to manage browser cookies from your streamlit code.


#### Basic usage

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

The cookie will default to expire in 720 minutes in the users browsers timezone.


#### Advanced usage

Pythons `CookieManager.set()` also supports setting most cookie flags/properties  e.g.

```Python
import pytz
import streamlit as st
from streamlitextras.webutils import get_user_timezone
from streamlitextras.cookiemanager import get_cookie_manager

user_tz = get_user_timezone()
expiry_date = (datetime.now(pytz.UTC) + timedelta(seconds=60*60))
cookie_expiry_time = expiry_date.astimezone(tz=pytz.timezone(user_tz))

cookie_manager = get_cookie_manager()
cookie_manager.set("my_cookie_name", "I expire in one hour", expires_at=cookie_expiry_time)
```

For a full list see the API docs.

###### Note

CookieManager will add a reference to the javascript universal-cookie class to both the JS globals `parent` and `window` object, so you can access it from the browser console or other parts of your app as `window.CookieManager`.

Some streamlit componenets run in iframes so you may need to use `parent.window.CookieManager`

Also note that this is a different CookieManager class to the Python CookieManager.