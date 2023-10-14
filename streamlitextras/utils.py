# File contains utility or helper functions
import os
from typing import Optional
from streamlit.runtime.uploaded_file_manager import UploadedFile


def repr_(
    cls, ignore_keys: Optional[list[str]] = None, only_keys: Optional[list[str]] = None
) -> str:
    """
    Returns a string detailing a class attributes from cls.__dict__
    Makes nice printing for __repr__ implementations

    :param ignore_keys: If provided, these keys will be not be included in the attribute string
    :param only_keys: If provided, these keys will be the only ones included in the attribute string
    """
    if not hasattr(cls, "__dict__"):
        return repr(cls)
    if not ignore_keys or only_keys:
        ignore_keys = []
    classname = cls.__class__.__name__

    try:
        args = ", ".join(
            [
                f"{k}={repr(v)}"
                for (k, v) in cls.__dict__.items()
                if k not in ignore_keys and (k in only_keys if only_keys else True)
            ]
        )
    except RecursionError:
        args = "Too much recursion"
    return f"{classname}({hex(id(cls))}, {args})"


def save_file(st_file_object: UploadedFile, to_path: str) -> str:
    """
    Saves a streamlit UploadedFile BytesIO object to the given relative path

    :param UploadedFile st_file_object: The UploadedFile bytes object to save to disk - contains filename and metadata
    :param str to_path: The relative path to a folder to save the file to
    :returns str: Will return the relative path which can be used as a URL
    """
    os.makedirs(to_path, exist_ok=True)
    path = os.path.join(to_path, st_file_object.name)
    with open(path, "wb") as f:
        f.write(st_file_object.getbuffer())
    return "/" + path


def where_stack():
    import inspect

    stack = inspect.stack()
    the_class = stack[1][0].f_locals["self"].__class__.__name__
    the_method = stack[1][0].f_code.co_name

    print("I was called by {}.{}()".format(the_class, the_method))
