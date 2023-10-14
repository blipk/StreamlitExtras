import base64
from io import BytesIO
from requests import get
from datetime import datetime

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile


class CustomHTML:
    """
    Class containing custom HTML/CSS to be injected into the streamlit app
    """

    @property
    def st_info_classes(self) -> list:
        """
        Classes used by st.info(), used for creating a custom info box with self.custom_el()
        """
        return ["st-at", "st-ax", "st-aw", "st-av", "st-au"]

    @property
    def adjust_st_style(self) -> str:
        """
        Hides the streamlit footer and menus and makes other adjustments
        """
        code = """
            <style>
            #MainMenu {display: none !important;}
            footer {display: none !important;}
            header {display: none !important;}
            div[class*="viewerBadge"] {display: none !important;}
            .block-container {padding-top: 0px;}

            div.stButton > button:first-child {
                background-color: #0E4176;
                color: #ffffff;
            }
            div.stButton > button:hover {
                background-color: #0E4176;
                color: #ff0000;
            }
            div.stButton > button:disabled, button[disabled] {
                background-color: #F0F2F6;
                color: grey;
            }
            p.a {
                font: bold 12px Courier;
            }
            </style>
            """
        return code

    @staticmethod
    def centered_image(image_path: str) -> None:
        """
        Creates 3 streamlit columns with a centered image

        :param str image_path: The URL or local path of an image
        This is currently unused.
        """

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write(" ")

        with col2:
            if image_path:
                st.image(image_path, use_column_width="always")
            else:
                st.image("https://static.streamlit.io/examples/dog.jpg")

        with col3:
            st.write(" ")

        st.image(image_path, use_column_width="always")

    @staticmethod
    def anchor_el(anchor_id: str):
        """
        Creates a div to be used as a # anchor

        :param str anchor_id: the string to set the id property to on the div element
        """
        return f"<div id='{anchor_id}' style='content-visibility: hidden; padding: 0px; margin: 0px;'>{anchor_id}</div>"

    @staticmethod
    def bytes_to_data_uri(
        byteslike_object: BytesIO | UploadedFile | bytes,
        mime_type: str | None = None,
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
        except:  # noqa: E722
            data = byteslike_object
        if not mime_type:
            mime_type = "application/octet-stream"
        uri = f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
        return uri

    @classmethod
    def download_link(
        cls,
        byteslike_object: BytesIO | UploadedFile | bytes,
        filename: str,
        link_text: str = "",
        mime_type: str | None = None,
    ) -> str:
        """
        Creates a data URI from a bytesIO object

        :param Union[BytesIO, UploadedFile] byteslike_object: BytesIO or bytes or any class that inherits them
        :param str filename: The filename presented for the download file
        :param str link_text: The text to put inside the link element, defaults to empty string
        :param Optional[str] mime_type: The mimetype to set on the data URI. Defaults to "application/octet-stream"
        """
        link_props = {
            "download": filename,
            "href": cls.bytes_to_data_uri(byteslike_object),
        }
        download_link = cls.custom_el(
            link_text, "a", custom_properties=link_props, classes=["auto-download"]
        )
        return download_link

    @staticmethod
    def custom_el(
        text: str,
        tag: str = "div",
        align: str = "",
        color: str = "",
        anchor: str = "",
        classes: list = [],
        extra_style: str = "",
        props: dict = {},
    ) -> str:
        """
        Creates HTML string for a custom element based on the function parameters.
        There is no validation so ensure calls to this function are correct.

        :param str text: the innerText/innerHTML of the element
        :param str tag: the HTML tag of the element
        :param str align: the CSS text-align property to apply to the element style
        :param str color: the css color property to apply to the element style
        :param str anchor: if provided, will put an empty div element with this value as an id next to the main element. used for creating anchors.
        :param list classes: list of css classes to apply to the class property of the element
        :param str extra_style: string of properly formatted CSS rules to be applied to the element style tag
        :param dict props: dictionary of properties and values to apply to the element in format {"property": "value"}
        """

        classes_string = ""
        for c in classes:
            classes_string += f"{c} "

        style_string = ""
        if align and align != "":
            style_string += f"text-align: {align};"
        if color and color != "":
            style_string += f"color: {color};"
        style_string += extra_style

        properties_string = ""
        for name, value in props.items():
            properties_string += f' {name}="{value}"'

        code = f"""<{tag} style="{style_string}" class="{classes_string}"{properties_string}>{text}</{tag}>"""
        if anchor != "":
            code = (
                f"<div id='{anchor}' style='padding: 0px; margin: 0px;'></div>" + code
            )
        return code

    @staticmethod
    def display_speaker(speaker_id: str) -> str:
        """
        Creates HTML text for a simple paragraph element with the innerText as speaker_id

        :param str speaker_id: The text to be inserted in the element innerText/innerHTML
        """
        code = f"""<p class="a">{speaker_id}</p>\n"""

        return code

    @staticmethod
    def display_text(text: str) -> str:
        """
        Creates HTML text for a styled paragraph element with the innerText as text

        :param str text: The text to be inserted into the paragraph innerText/innerHTML
        """
        code = f"""<p style="font-size: medium; font-family: sans-serif">{text}</p>\n"""
        return code

    @staticmethod
    def display_table(table_data: list[list], style: str = "") -> str:
        """
        Creates HTML table based on table_data which is a 2D list
        Each list item is a set of columns. The first item is the header.

        :param list[list] table_data: The data to fill the table in
        :param str style: The CSS style tag to apply to the table
        """
        table = f'<table style="{style}">\n'
        for i, row in enumerate(table_data):
            tag = "<th>" if i == 0 else "<td>"
            table += "<tr>\n"
            for column in row:
                table += f"""{tag}{column}{tag.replace("<", "</")}\n"""
            table += "</tr>\n"
        table += "</table>"

        return table

    @staticmethod
    def display_audio(
        audio_file_url: str,
        timestamp: str | int = "",
        id: str = "audio",
        classes: list = [],
    ) -> str:
        """
        Creates a HTML audio element with a specified id and special class,
        this enables more advanced handling of the elements than st.audio()

        :param str audio_file_url: The url to the audio file for the element
        :param str Union[str, int]: The timestamp in the format HH:MM:SS to apply to the URL fragment, alternatively can be the number of seconds
        :param str id: The id property of the audio element
        :param list classes: list of css classes to apply to the class property of the element
        """
        classes_string = "stAudio customAudio"
        for c in classes:
            classes_string += f" {c}"

        audio = f"""
        <audio id="{id}" controls preload
            src="{audio_file_url}{"#t="+str(timestamp) if timestamp != "" and timestamp != 0 else ""}"
            class="{classes_string}"
            style="width: 100%;"
            oncanplaythrough="">
        </audio>
        """

        return audio

    lottie_url = (
        "https://lottie.host/250d8ce6-e7eb-43a7-ab4f-1d78edc49b9d/2TLv74crQZ.json"
    )

    @classmethod
    def load_lottieurl(
        cls,
        lottie_url: str | None = None,
    ) -> dict | None:
        """
        Loads and returns JSON from the lottie library
        This is used for animations
        """
        if not lottie_url:
            lottie_url = cls.lottie_url
        r = get(lottie_url)
        if r.status_code != 200:
            return None
        return r.json()

    @property
    def lottie_data(self):
        return self.load_lottieurl()


custom_html = CustomHTML()
audio_extensions = ["PCM", "WMA", "MP4", "M4A", "WAV", "AIFF", "MP3", "AAC"]


def readable_datestr(target_datetime: datetime, format: str = "%d/%m/%Y"):
    return target_datetime.strftime(format)
