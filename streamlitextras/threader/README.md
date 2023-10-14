# Streamlit Extras Threader

Utility functions to make running threading.Threads easy in streamlit.

#### Basic usage

This requires `runOnSave = true` in `./streamlit/config.toml`,
and you will need to create an empty file named `reruntrigger.py` in the root of your project.

```Python
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
```

#### Advanced usage

Mostly you may want to use `streamlit_thread(my_threaded_function, rerun_st=False)` if you don't want streamlit to rerun after the thread.

**NOTE** The rerun trigger will rerun all streamlit sessions for all users on your site.

To get around this, generate or use a unique id you have for each user session,
use it in this modules function arguments and then import the rerun trigger for that session e.g.

```Python
import importlib
unique_id = st.session_state.get("session_uid", generate_uniqueid())
st.session_state["session_uid"] = unique_id
importlib.import_module(f"reruntrigger_{unique_id}")


from streamlitextras.threader import trigger_rerun
st.button("Rerun for this session only", on_click=trigger_rerun, args=(unique_id,))
```

See the [API docs](https://streamlitextras.readthedocs.io/en/latest/api/streamlitextras.html) or the source file for function argument reference.
