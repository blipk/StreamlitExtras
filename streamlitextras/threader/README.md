# Streamlit Extras Threader

Utility functions to make running threading.Threads easy in streamlit.

#### Basic usage

This requires `runOnSave = true` in `./streamlit/config.toml`

```Python
import time
import streamlit as st
from streamlitextras.threader import lock, trigger_rerun, streamlit_thread, get_thread, last_trigger_time

router = None
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

See the API docs or the source file for function argument reference.