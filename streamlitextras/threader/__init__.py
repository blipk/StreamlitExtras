import os
import time
import threading
from . import reruntrigger
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx, RerunException
from typing import Callable, Optional

# script_dir = os.path.dirname(os.path.realpath(__file__))
script_dir = os.getcwd()
trigger_file_path = os.path.join(script_dir, "reruntrigger.py")
if not os.path.exists(trigger_file_path):
    with open(trigger_file_path, "w") as f:
        f.write(f"timestamp = {time.time()}")

lock = threading.Lock()

def last_trigger_time() -> int:
    """
    Returns the seconds since last writing the trigger file
    """
    modified_time = os.path.getmtime(trigger_file_path)
    modified_time_seconds = time.time() - modified_time
    return modified_time_seconds

def trigger_rerun(last_write_margin: int = 1, delay: int = 0) -> None:
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
            print("Writing trigger", trigger_file_path, flush=True)
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
                *args, **kwargs) -> None:
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
                    delay: int = 0) -> str:
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
    thread = PropagatingThread(target=thread_wrapper, args=args, kwargs=kwargs)
    add_script_run_ctx(thread, get_script_run_ctx())
    time.sleep(0.1)
    thread.start()
    return thread.name

def get_thread(thread_name) -> Optional[threading.Thread]:
    """
    Gets the threading.Thread instance thats name attribute matches thread_name

    :param thread_name: The name attribute of the thread to look for.

    :returns: The threading.Thread or None if theres no thread with the supplied thread_name
    """
    threads = threading.enumerate()
    target_thread = None
    for thread in threads:
        if thread.name == thread_name:
            target_thread = thread
            break
    return target_thread

class PropagatingThread(threading.Thread):
    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except RerunException as e:
            self.exc = e
        except BaseException as e:
            self.exc = e
            raise

    def join(self, timeout=None):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
            # raise RuntimeError('Exception in thread') from self.exc
        return self.ret
