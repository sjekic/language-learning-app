"""One owner for trigger selection, lease renewal, and acknowledgement."""
import json
import os
from contextvars import ContextVar
from threading import Event, Thread

from azure.storage.blob import BlobServiceClient
from common.contracts import validate_trigger

_active_claim = ContextVar("active_trigger_claim", default=None)


def check_claim():
    """Stop additional generation/writes after a known lease-renewal failure."""
    claim = _active_claim.get()
    if claim is not None:
        claim.check()


class TriggerLease:
    """A finite lease recovers after a crashed process; long jobs renew it."""
    def __init__(self, blob):
        self.lease = blob.acquire_lease(lease_duration=60)
        self.stop = Event()
        self.error = None
        self.thread = Thread(target=self._renew, daemon=True)

    def _renew(self):
        while not self.stop.wait(20):
            try:
                self.lease.renew()
            except Exception as exc:
                self.error = exc
                return

    def __enter__(self):
        self.thread.start()
        return self

    def check(self):
        if self.error is not None:
            raise RuntimeError("Lost trigger lease; work must be retried") from self.error

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=5)
        try:
            self.lease.release()
        except Exception as exc:
            # Deleting the acknowledged blob also removes its lease.
            if getattr(exc, "status_code", None) not in (404, 409, 412):
                print(f"Could not release trigger lease: {exc}")


def run_pending(job, worker, replica_index=None):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING not set")
    service = BlobServiceClient.from_connection_string(connection_string)
    container = service.get_container_client("stories")
    blobs = []
    for suffix in ("-scheduled", ""):
        blobs.extend(container.list_blobs(name_starts_with=f"triggers/{job}{suffix}/"))
    blobs.sort(key=lambda blob: blob.name)
    if replica_index is not None:
        if replica_index < 0:
            raise ValueError("JOB_COMPLETION_INDEX must not be negative")
        # A replica index is a starting hint, not exclusive ownership. Leases
        # provide ownership; scanning past poison/busy entries prevents starvation.
        if blobs:
            start = replica_index % len(blobs)
            blobs = blobs[start:] + blobs[:start]
    failures = 0
    completed = 0
    for item in blobs:
        blob = container.get_blob_client(item.name)
        try:
            claim = TriggerLease(blob)
        except Exception as exc:
            if getattr(exc, "status_code", None) in (404, 409):
                continue  # Already claimed or acknowledged by another replica.
            raise
        try:
            with claim:
                payload = json.loads(blob.download_blob(lease=claim.lease).readall())
                validate_trigger(payload, job)
                context = _active_claim.set(claim)
                try:
                    worker(payload)
                finally:
                    _active_claim.reset(context)
                claim.check()
                blob.delete_blob(lease=claim.lease)
                completed += 1
            if replica_index is not None:
                break  # One successful batch per chunk replica.
        except Exception as exc:
            failures += 1
            print(f"Failed {item.name}; trigger retained for retry: {exc}")
    if failures:
        raise RuntimeError(f"{failures} {job} trigger(s) failed; retained for retry")
    return completed


def enqueue(job, story_id, trigger_id, **parameters):
    """Stable names make retrying downstream dispatch safe (create if absent)."""
    check_claim()
    service = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
    payload = {"story_id": story_id, "trigger_id": trigger_id, "job_name": job, **parameters}
    validate_trigger(payload, job)
    blob = service.get_blob_client(container="stories", blob=f"triggers/{job}-scheduled/{trigger_id}.json")
    try:
        blob.upload_blob(json.dumps(payload), overwrite=False)
    except Exception as exc:
        if getattr(exc, "status_code", None) != 409:
            raise
        existing = json.loads(blob.download_blob().readall())
        if not isinstance(existing, dict) or any(existing.get(key) != value for key, value in payload.items()):
            raise ValueError(f"Conflicting trigger already exists: {trigger_id}") from exc
