from collections.abc import Callable, Iterable, Mapping
import os
import time
import threading
from streamlit.runtime.scriptrunner import (
    add_script_run_ctx,
    get_script_run_ctx,
    RerunException,
    ScriptRunContext,
)
from typing import Any, Callable, Optional

# script_dir = os.path.dirname(os.path.realpath(__file__))
script_dir = os.getcwd()

default_id = "default"


def trigger_file_path(unique_id: str = default_id) -> str:
    trigger_file_path = os.path.join(script_dir, f"reruntrigger_{unique_id}.py")
    if not os.path.exists(trigger_file_path):
        with open(trigger_file_path, "w") as f:
            f.write(f"timestamp = {time.time()}")
    return trigger_file_path


lock = threading.Lock()


def last_trigger_time(unique_id: str = default_id) -> int:
    """
    Returns the seconds since last writing the trigger file
    """
    modified_time = os.path.getmtime(trigger_file_path(unique_id))
    modified_time_seconds = time.time() - modified_time
    return modified_time_seconds


def trigger_rerun(
    unique_id: str = default_id, last_write_margin: int = 1, delay: int = 0
) -> None:
    """
    Triggers treamlit to rerun the current page state.
    runOnSave must be set to true in config.toml

    :param str unique_id: Unique ID to be triggered, should be set per session e.g. user id or a hash you create in their session state.
    :param int last_write_margin:
        If the file was modified less than this many seconds ago, the rerun will not be performed
    :param int delay: sleep for this many seconds before writing the rerun trigger
    """
    if delay:
        time.sleep(delay)
    with lock:
        modified_time_seconds = last_trigger_time(unique_id)
        if last_write_margin == 0 or modified_time_seconds > last_write_margin:
            trigger_file = trigger_file_path(unique_id)
            print("Writing trigger", trigger_file, flush=True)
            with open(trigger_file, "w") as f:
                f.write(f"timestamp = {time.time()}")
    # https://github.com/streamlit/streamlit/issues/1792
    # https://discuss.streamlit.io/t/using-streamlit-with-multithreading/30990
    # https://discuss.streamlit.io/t/how-to-run-a-subprocess-programs-using-thread-inside-streamlit/2440/2
    # https://discuss.streamlit.io/t/how-to-monitor-the-filesystem-and-have-streamlit-updated-when-some-files-are-modified/822/3


def thread_wrapper(
    thread_func,
    rerun_st=True,
    last_write_margin: int = 1,
    delay: int = 0,
    trigger_unique_id: str = default_id,
    *args,
    **kwargs,
) -> None:
    """
    Wrapper for running thread functions
    For parameters see streamlit_thread() and trigger_rerun()
    """
    # print("Hashseed in thread:", os.environ.get("PYTHONHASHSEED", False))
    thread_func(*args, **kwargs)
    if rerun_st is True:
        trigger_rerun(trigger_unique_id, last_write_margin, delay)


def streamlit_thread(
    thread_func: Callable,
    args: tuple = (),
    kwargs: dict = {},
    rerun_st: bool = True,
    last_write_margin: int = 1,
    delay: int = 0,
    script_run_context: ScriptRunContext | None = None,
    autostart: bool = True,
    trigger_unique_id: str = default_id,
    error_handler: Callable | None = None,
) -> str:
    """
    Spawns and starts a threading.Thread that runs thread_func with the passed args and kwargs

    :param Callable thread_func: The function to run in the thread
    :param tuple args: The args to pass to the function in the thread
    :param dict kwargs: The kwargs to pass to the function in the thread
    :param bool rerun_st: Whether to rerun streamlit after the thread function finishes

    :param Callable error_handler: Error handler function that takes the thread exception as an argument

    :returns: The name of the thread. Can use get_thread to get the threading.Thread instance
    """
    # print("Thread entry hashseed:", os.environ.get("PYTHONHASHSEED", False))
    args = (thread_func, rerun_st, last_write_margin, delay, trigger_unique_id, *args)
    thread = PropagatingThread(
        target=thread_wrapper, error_handler=error_handler, args=args, kwargs=kwargs
    )

    if not script_run_context:
        script_run_context = get_script_run_ctx()
    add_script_run_ctx(thread, script_run_context)

    time.sleep(0.4)
    if autostart is True:
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
    def __init__(self, *args, **kwargs) -> None:
        self.error_handler = kwargs.get("error_handler", None)
        del kwargs["error_handler"]
        super().__init__(*args, **kwargs)

    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except RerunException as e:
            self.exc = e
        except BaseException as e:
            self.exc = e
            if self.error_handler and callable(self.error_handler):
                self.error_handler(e)
            else:
                raise

    def join(self, timeout=None):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            if self.error_handler and callable(self.error_handler):
                self.error_handler(self.exc)
            else:
                raise self.exc
            # raise RuntimeError('Exception in thread') from self.exc
        return self.ret
