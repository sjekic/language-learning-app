from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from common.triggers import check_claim
import os
import json

blob = None


def get_client():
    global blob
    if blob is None:
        blob = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
    return blob

def upload_text(container, path, text):
    check_claim()
    get_client().get_blob_client(container=container, blob=path).upload_blob(
        text, overwrite=True
    )

def download_text(container, path):
    try:
        client = get_client().get_blob_client(container=container, blob=path)
        return client.download_blob().readall().decode("utf-8")
    except Exception as e:
        print(f"Error downloading {container}/{path}: {e}")
        raise

def upload_json(container, path, data):
    check_claim()
    try:
        client = get_client().get_blob_client(container=container, blob=path)
        client.upload_blob(json.dumps(data), overwrite=True)
        print(f"Uploaded {container}/{path}")
    except Exception as e:
        print(f"Error uploading {container}/{path}: {e}")
        raise

def upload_file(container, path, local_path):
    check_claim()
    with open(local_path, "rb") as f:
        get_client().get_blob_client(container=container, blob=path).upload_blob(
            f, overwrite=True
        )

def list_blobs(container, prefix):
    try:
        container_client = get_client().get_container_client(container)
        return [b.name for b in container_client.list_blobs(name_starts_with=prefix)]
    except Exception as e:
        print(f"Error listing blobs in {container}/{prefix}: {e}")
        raise


def download_json_if_exists(container, path):
    try:
        return json.loads(download_text(container, path))
    except ResourceNotFoundError:
        return None
