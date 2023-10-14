import base64
import hashlib
import binascii
import datetime
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from google.oauth2 import service_account
from google.cloud import storage
from google.cloud.storage.retry import _should_retry
from google.api_core import retry

from typing import Optional, Iterable, Union, Tuple
from io import BytesIO

# Default project and bucket
default_gproject = st.secrets["gcp_service_account"]["project_id"]
default_bucket = st.secrets["firebase"]["storageBucket"]

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    dict(st.secrets["gcp_service_account"])
)
client = storage.Client(credentials=credentials)

_INITIAL_DELAY = 1.0  # seconds
_MAXIMUM_DELAY = 4.0
_DELAY_MULTIPLIER = 2.0
_DEADLINE = 60.0
retry_custom = retry.Retry(
    _should_retry, _INITIAL_DELAY, _MAXIMUM_DELAY, _DELAY_MULTIPLIER, _DEADLINE
)


def compute_bytes_md5hash(data: bytes):
    md5hex = hashlib.md5(data).hexdigest()
    encoded_bytes = base64.b64encode(binascii.unhexlify(md5hex))
    sig = encoded_bytes.rstrip(b"\n").decode("UTF-8")
    return sig


def get_buckets(
    project: str = default_gproject,
    prefix: Optional[str] = None,
    page_size: int = 500,
    timeout: int = 8,
    retry: retry.Retry = retry_custom,
    print_names: bool = False,
) -> Iterable[storage.Bucket]:
    buckets = client.list_buckets(
        project=project,
        prefix=prefix,
        page_size=page_size,
        timeout=timeout,
        retry=retry,
    )
    if print_names:
        for bucket in buckets:
            print(bucket)
    return buckets


def get_blobs(
    bucket_or_name: Union[str, storage.Bucket] = default_bucket,
    prefix: Optional[str] = None,
    page_size: int = 500,
    timeout: int = 8,
    retry: retry.Retry = retry_custom,
    print_names: bool = False,
) -> Optional[Iterable[storage.Blob]]:
    """
    Prints a list of all the blobs in the specified storage bucket,
    and returns them as an iterable
    """
    blobs = client.list_blobs(
        bucket_or_name, prefix=prefix, page_size=page_size, timeout=timeout, retry=retry
    )
    bucket_name = bucket_or_name if type(bucket_or_name) == str else bucket_or_name.name
    if print_names:
        for blob in blobs:
            print(blob)

    return blobs


def get_bucket(
    bucket_name: str, timeout: int = 8, retry: retry.Retry = retry_custom
) -> Optional[storage.Bucket]:
    bucket = client.lookup_bucket(bucket_name, timeout=timeout, retry=retry)
    return bucket


def create_bucket(
    bucket_name: str,
    project: str = default_gproject,
    billing_project: str = default_gproject,
    bucket_location: str = "us-east1",
    timeout: int = 8,
    retry: retry.Retry = retry_custom,
) -> storage.bucket.Bucket:
    bucket = client.create_bucket(
        bucket_name,
        location=bucket_location,
        project=project,
        user_project=billing_project,
        timeout=timeout,
        retry=retry,
    )
    return bucket


def upload_blob_data(
    blob_name: str,
    blob_data: Union[UploadedFile, str],
    bucket_name: str = default_bucket,
    content_type: Optional[str] = None,
    timeout: int = 8,
    retry: retry.Retry = retry_custom,
) -> Tuple[storage.Blob, str]:
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    if blob.exists(client, timeout=timeout, retry=retry):
        return (blob, get_blob_url(blob))

    if type(blob_data) == UploadedFile:
        blob.upload_from_file(
            blob_data, content_type=content_type, timeout=timeout, retry=retry
        )
    elif type(blob_data) == str:
        blob.upload_from_string(
            blob_data, content_type=content_type, timeout=timeout, retry=retry
        )

    return (blob, get_blob_url(blob))


def get_blob_url(blob: storage.Blob):
    url = blob.generate_signed_url(
        expiration=datetime.timedelta(minutes=60), version="v4", method="GET"
    )
    return url


def download_blob_data(
    bucket_name: str, blob_name: str, return_type: str = "bytes"
) -> Union[BytesIO, str]:
    bucket = client.bucket(bucket_name)
    content = None
    if return_type == "bytes":
        content = bucket.blob(blob_name).download_as_bytes()
    elif return_type == "string":
        content = bucket.blob(blob_name).download_as_text(encoding="utf-8")

    return content
