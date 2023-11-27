import os
import sys
import ast
import loguru
import dateutil.parser
from loguru._logger import Logger
import streamlit as st
from streamlitextras.utils import repr_

dev_emulation = os.environ.get("DEV_EMULATION", False)

_LOGGER = loguru.logger
log_folder = "logs"
log_filename = "streamlit.log"

module_filter = ""
default_format = "{time} | {level: <8} | {name}:{module}:{function}:{file}:{line} | {message} | {extra}"
detailed_format = "{time} | {level: <8} | {name}:{module}:{function}:{file.path}:{line} | {message} | {extra} | {exception} | {process.name}:{process} {thread.name}:{thread}"

colour_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{file}</cyan>:<cyan>{line}</cyan> | <green>{extra}</green> | "
    "\n<level>{message}</level>"
)

colour_detailed_format = (
    "<red>{time:YYYY-MM-DD HH:mm:ss.SSS}</red> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{file.path}</cyan>:<cyan>{line}</cyan> | "
    "\n<green>{extra}</green><level>{message}</level> | "
    "<level>{exception}</level> | "
    "<level>{process.name}:{process} @ {thread.name}:{thread}</level>"
)
if dev_emulation:
    colour_format = colour_format.replace("file", "file.path")

handlers = [
    {
        "sink": os.path.join(log_folder, log_filename),
        "rotation": "250 MB",
        "enqueue": True,
        "format": default_format,
        "filter": module_filter,
        "level": "INFO",
        "catch": True,
    },
    {
        "sink": os.path.join(log_folder, "debug_" + log_filename),
        "rotation": "250 MB",
        "enqueue": True,
        "format": detailed_format,
        "filter": module_filter,
        "level": "TRACE",
        "backtrace": True,
        "diagnose": True,
        "catch": True,
    },
    # Errors will be logged to sys.stdout
    # {"sink": sys.stderr,
    # "format": colour_detailed_format,
    # "filter": module_filter,
    # "level": "ERROR",
    # "backtrace": True,
    # "colorize": True},
    {
        "sink": sys.stdout,
        "format": colour_format,
        "filter": module_filter,
        "level": "DEBUG",
        "colorize": True,
    },
]


def process_log_line(log_line: str):
    """
    Process a log line formatted from this module into a dictionary of its sections.

    :param str log_line: The log line to process
    """
    if not log_line:
        return None
    time, level, namespace, message, extra, exception, exec = log_line.split(" | ")
    level = level.strip()
    name, module, function_name, file_path, line = namespace.split(":")

    try:
        process, thread = exec.split(" @ ")
    except:
        process = exec.split(" ")[0]
        thread = " ".join(exec.split(" ")[1:])
    process_name, process_id = process.split(":")
    thread_name, thread_id = thread.split(":")

    log_obj = {
        "log_line": log_line,
        "level": level,
        "time": dateutil.parser.isoparse(time),
        "message": message,
        "extra": ast.literal_eval(extra),
        "exception": exception,
        "namespace": namespace,
        "name": name,
        "module": module,
        "function_name": function_name,
        "file_path": file_path,
        "line": line,
        "process_name": process_name,
        "process_id": process_id,
        "thread_name": thread_name,
        "thread_id": thread_id,
    }
    return log_obj


def default_bind(include_session_state: bool = False):
    """
    Generate a dict from st.session_state to be stored with every log line
    """
    extra = {
        "user": repr(st.session_state.get("user", None)),
    }

    if include_session_state:
        extra["session_state"] = (
            {k: f"{v}" for k, v in st.session_state.to_dict().items()},
        )

    for k in list(extra.keys()):
        if not extra[k]:
            del extra[k]

    return extra


def bind_log(extras = None) -> Logger:
    """
    Bind the logger to the session state dictionary
    """
    global log
    merged = {**default_bind(), **(extras if extras else {})}

    for k in list(merged):
        merged[k] = str(merged[k])

    log = _LOGGER.bind(**merged)
    return log


log: Logger


def __getattr__(name):
    global log
    if name == "log":
        log = bind_log()
        return log
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


sinks = _LOGGER.configure(handlers=handlers, activation=[("", True)])
