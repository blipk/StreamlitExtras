import time
import html
import uuid
import base64
import streamlit as st
from io import BytesIO
from typing import Union, Optional
from streamlit_javascript import st_javascript
from streamlit.runtime.uploaded_file_manager import UploadedFile


def stxs_javascript(source: str) -> None:
    """
    Runs javascript on the top level context of the page.

    Does this by embedding an iframe that attaches a script tag to its parent.

    :param str source: The script source to embed in the <script></script> element
    """
    div_id = uuid.uuid4()

    st.markdown(
        f"""
    <div style="display:none" id="{div_id}">
        <iframe src="javascript: \
            var script = document.createElement('script'); \
            script.type = 'text/javascript'; \
            script.text = {html.escape(repr(source))}; \
            var thisDiv = window.parent.document.getElementById('{div_id}'); \
            var rootDiv = window.parent.parent.parent.parent.document.getElementById('root'); \
            rootDiv.appendChild(script); \
            thisDiv.parentElement.parentElement.parentElement.style.display = 'none'; \
        "/>
    </div>
    """,
        unsafe_allow_html=True,
    )
    time.sleep(0.1)
    return True


def get_user_timezone(default_tz: Optional[str] = None) -> Optional[str]:
    """
    Uses javascript to get the tz database name for the browser/users timezone

    :param Optional[str] default_tz: value to return if the operation fails. Defaults to UTC

    :returns Optional[str]:
        The tz database name for the timezone,
        or None if the operation fails and default_tz isn't set, or isn't supported by the browser (unlikely)
    """
    if not default_tz:
        default_tz = "Etc/UTC"

    timezone = st_javascript(
        """await (async () => {
            const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone
            console.log(userTimezone)
            return userTimezone
        })().then(returnValue => returnValue)"""
    )
    if timezone == 0:  # st_javascript returns 0 for null/undefined
        timezone = default_tz
    return timezone


def scroll_page(x: int = 0, y: int = 0):
    """
    Runs javascript to scroll the streamlit main section
    Defaults to scrolling to the top if no arguments are passed

    :param int x: the x coordinate to scroll to
    :param int y: the y coordinate to scroll to
    """
    stxs_javascript(
        f"""parent.document.querySelector(`section[class*="main"`).scroll({x}, {y})"""
    )


def bytes_to_data_uri(
    byteslike_object: Union[BytesIO, UploadedFile, bytes],
    mime_type: Optional[str] = None,
) -> str:
    """
    Creates a data URI from a bytesIO object

    :param Union[BytesIO, UploadedFile] byteslike_object: BytesIO or bytes or any class that inherits them
    :param str mime_type: The mimetype to set on the data URI
    :returns: The data URI as a string
    """
    data = None
    try:
        data = byteslike_object.getvalue()
    except:
        data = byteslike_object
    if not mime_type:
        mime_type = "application/octet-stream"
    uri = f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
    return uri


def trigger_download(download_uri: str, filename: str):
    """
    Uses javascript and a data URI on a link element to trigger a download for the user

    :param str download_uri: properly formatted data uri to place on link elements href
    :param str filename: filename to be placed on the link elements download attribute
    """
    auto_downloaded = stxs_javascript(
        f"""(async () => {{
            console.log("Creating download link..")
            var link = document.createElement('a');
            link.innerText = ""
            link.href = "{download_uri}";
            link.target = "_blank";
            link.download = "{filename}";
            link.click();
            await new Promise(r => setTimeout(r, 2000));
            //window.open(link.href, "_blank")
        }})();"""
    )
    time.sleep(
        1
    )  # Give the page some time to render the element before the page rerenders
    return auto_downloaded


def convert_millis(milliseconds: int, always_include_hours: bool = False) -> str:
    """
    Convert milliseconds to a string timestamp in the format HH:MM:SS or MM:SS

    :param int milliseconds: The amount of milliseconds to convert to a timestamp
    :param bool always_include_hours: Always include the HH: part of the timestamp even if 00.
    """
    seconds = int((milliseconds / 1000) % 60)
    minutes = int((milliseconds / (1000 * 60)) % 60)
    hours = int((milliseconds / (1000 * 60 * 60)) % 24)
    timestamp_text = ""
    if hours > 0:
        timestamp_text += f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        if always_include_hours:
            timestamp_text += f"{hours:02d}:"
        timestamp_text += f"{minutes:02d}:{seconds:02d}"

    return timestamp_text
