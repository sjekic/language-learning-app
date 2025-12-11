from azure.storage.blob import BlobServiceClient
import os
import json

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

blob = BlobServiceClient.from_connection_string(connection_string)

def upload_text(container, path, text):
    blob.get_blob_client(container=container, blob=path).upload_blob(
        text, overwrite=True
    )

def download_text(container, path):
    try:
        client = blob.get_blob_client(container=container, blob=path)
        return client.download_blob().readall().decode("utf-8")
    except Exception as e:
        print(f"Error downloading {container}/{path}: {e}")
        raise

def upload_json(container, path, data):
    try:
        client = blob.get_blob_client(container=container, blob=path)
        client.upload_blob(json.dumps(data), overwrite=True)
        print(f"Uploaded {container}/{path}")
    except Exception as e:
        print(f"Error uploading {container}/{path}: {e}")
        raise

def upload_file(container, path, local_path):
    with open(local_path, "rb") as f:
        blob.get_blob_client(container=container, blob=path).upload_blob(
            f, overwrite=True
        )

def list_blobs(container, prefix):
    try:
        container_client = blob.get_container_client(container)
        return [b.name for b in container_client.list_blobs(name_starts_with=prefix)]
    except Exception as e:
        print(f"Error listing blobs in {container}/{prefix}: {e}")
        raise
