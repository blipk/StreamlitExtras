# Streamlit Extras Logger

This is mostly used internally by Streamlit Extras, however you can use it as well to log in your app.
See the Loguru documentation on PyPI for more information.

It will log to stdout (console/terminal) as well as to two files in `./logs`


#### Basic usage

```Python
import streamlit as st
from streamlitextras.logger import log

def main():
    log.debug("My app just started!")
    st.write("My app")

if __name__ == "__main__":
    main()
```

### Advanced usage

The files in logs will contain trailing dicts of st.session_state() which can be processed and used to display logs in a page like so:

```Python

import os
import pytz
import streamlit as st
from streamlitextras.webutils import get_user_timezone
from streamlitextras.logger import log, process_log_line

def log_page():
    log_file = "logs/debug_streamlit.log"
    if not os.path.exists(log_file):
        st.write("No log file.")
        return

    page_timezone = pytz.timezone(get_user_timezone())

    with open(log_file, "r") as f:
        log_contents = f.read()

    log_levels = {}
    log_lines = log_contents.split("\n")

    for line in log_lines:
        log_obj = process_log_line(line)
        if not log_obj:
            continue
        level = log_obj["level"]
        if level not in log_levels:
            log_levels[level] = []
        log_levels[level].append(log_obj)

    log_level_names = [str(name) for name in log_levels.keys()]
    option = st.selectbox("Log level:", log_level_names)

    timestamps = {}
    for log_obj in reversed(log_levels[option]):
        user = log_obj["extra"]["user"] if "user" in log_obj["extra"] else None
        time = log_obj["time"].astimezone(page_timezone)
        formatted_time = time.strftime("%a %d %b, %H:%M:%S")
        key = (formatted_time, user)
        if key not in timestamps:
            timestamps[key] = []
        timestamps[key].append(log_obj)

    for key, log_objects in timestamps.items():
        timestamp, timestamp_user = key
        columns = st.columns(2)
        info_display = f"""{timestamp}<br>{timestamp_user}"""
        columns[0].markdown(info_display, unsafe_allow_html=True)

        count = 1
        counter = None
        last_line = None
        for log_obj in reversed(log_objects):
            extra = log_obj["extra"]
            user = extra["user"] if "user" in extra else None

            if count > 1:
                counter.write(count)

            if len(extra["session_state"]) == 0:
                if last_line and log_obj["message"] == last_line["message"]:
                    count += 1
                else:
                    columns[1].write(log_obj["message"])
                    counter = columns[1].container()
            else:
                if last_line and log_obj["message"] == last_line["message"] and extra == last_line["extra"]:
                    count += 1
                else:
                    with columns[1].expander(log_obj["message"]):
                        st.write(extra)
                    counter = columns[1].container()

            if log_obj["exception"]:
                st.write(log_obj["exception"])

            last_line = log_obj
        st.write("---")
```

See the `process_log_line()` definition for more information.