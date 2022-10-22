import os
import time
import threading
from . import reruntrigger
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from typing import Callable

script_dir = os.path.dirname(os.path.realpath(__file__))
trigger_file_path = os.path.join(script_dir, "reruntrigger.py")

lock = threading.Lock()

def last_trigger_time() -> int:
    """
    Returns the seconds since last writing the trigger file
    """
    modified_time = os.path.getmtime(trigger_file_path)
    modified_time_seconds = time.time() - modified_time
    return modified_time_seconds

def trigger_rerun(last_write_margin: int = 1, delay: int = 0):
    """
    Triggers treamlit to rerun the current page state.
    runOnSave must be set to true in config.toml

    :param int last_write_margin:
        If the file was modified less than this many seconds ago, the rerun will not be performed
    :param int delay: sleep for this many seconds before writing the rerun trigger
    """
    if delay:
        time.sleep(delay)
    with lock:
        modified_time_seconds = last_trigger_time()
        if last_write_margin == 0 or modified_time_seconds > last_write_margin:
            print("Writing trigger", flush=True)
            with open(trigger_file_path, "w") as f:
                f.write(f"timestamp = {time.time()}")
    # https://github.com/streamlit/streamlit/issues/1792
    # https://discuss.streamlit.io/t/using-streamlit-with-multithreading/30990
    # https://discuss.streamlit.io/t/how-to-run-a-subprocess-programs-using-thread-inside-streamlit/2440/2
    # https://discuss.streamlit.io/t/how-to-monitor-the-filesystem-and-have-streamlit-updated-when-some-files-are-modified/822/3

def thread_wrapper(thread_func,
                rerun_st = True,
                last_write_margin: int = 1,
                delay: int = 0,
                *args, **kwargs):
    """
    Wrapper for running thread functions
    For parameters see streamlit_thread() and trigger_rerun()
    """
    # print("Hashseed in thread:", os.environ.get("PYTHONHASHSEED", False))
    thread_func(*args, **kwargs)
    if rerun_st == True:
        trigger_rerun(last_write_margin, delay)

def streamlit_thread(thread_func: Callable,
                    args: tuple = (),
                    kwargs: dict = {},
                    rerun_st: bool = True,
                    last_write_margin: int = 1,
                    delay: int = 0):
    """
    Spawns and starts a threading.Thread that runs thread_func with the passed args and kwargs

    :param Callable thread_func: The function to run in the thread
    :param tuple args: The args to pass to the function in the thread
    :param dict kwargs: The kwargs to pass to the function in the thread
    :param bool rerun_st: Whether to rerun streamlit after the thread function finishes

    :returns: The name of the thread. Can use get_thread to get the threading.Thread instance
    """
    # print("Thread entry hashseed:", os.environ.get("PYTHONHASHSEED", False))
    args = (thread_func, rerun_st, last_write_margin, delay, *args)
    thread = threading.Thread(target=thread_wrapper, args=args, kwargs=kwargs)
    add_script_run_ctx(thread, get_script_run_ctx())
    time.sleep(0.1)
    thread.start()
    return thread.name

def get_thread(thread_name):
    """
    Gets the threading.Thread instance thats name attribute matches thread_name

    :param thread_name:
        The name attribute of the thread to look for, or None if it's not found.
    """
    threads = threading.enumerate()
    target_thread = None
    for thread in threads:
        if thread.name == thread_name:
            target_thread = thread
            break
    return target_thread