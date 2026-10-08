"""Focused job utilities, contracts, storage and lease tests without global SDK mocks."""
import importlib
import json
from unittest.mock import Mock, patch

import pytest
from tests import test_job_pipeline as pipeline


@pytest.fixture
def job_env():
    environment = pipeline.JobPipelineTests(methodName="runTest")
    environment.setUp()
    try:
        yield environment
    finally:
        environment.doCleanups()


class TestUtils:
    def test_read_file(self, job_env, tmp_path):
        utils = importlib.import_module("common.utils")
        path = tmp_path / "test.txt"
        path.write_text("test content")
        assert utils.read_file(str(path)) == "test content"

    def test_read_file_nonexistent(self, job_env, tmp_path):
        with pytest.raises(FileNotFoundError):
            importlib.import_module("common.utils").read_file(str(tmp_path / "missing.txt"))

    def test_write_json(self, job_env, tmp_path):
        path = tmp_path / "nested" / "test.json"
        importlib.import_module("common.utils").write_json(str(path), {"key": "value"})
        assert json.loads(path.read_text()) == {"key": "value"}

    def test_write_text(self, job_env, tmp_path):
        path = tmp_path / "nested" / "test.txt"
        importlib.import_module("common.utils").write_text(str(path), "test content")
        assert path.read_text() == "test content"


class TestStorage:
    def test_upload_and_download_text(self, job_env):
        storage = importlib.import_module("common.storage")
        storage.upload_text("stories", "text.txt", "hello")
        assert storage.download_text("stories", "text.txt") == "hello"

    def test_optional_json_only_treats_not_found_as_absent(self, job_env):
        storage = importlib.import_module("common.storage")
        assert storage.download_json_if_exists("stories", "missing.json") is None
        with patch.object(storage, "download_text", side_effect=pipeline.StorageError("access denied", 403)):
            with pytest.raises(pipeline.StorageError):
                storage.download_json_if_exists("stories", "missing.json")

    def test_invalid_json_is_not_treated_as_absent(self, job_env):
        job_env.storage.data["invalid.json"] = b"not json"
        with pytest.raises(ValueError):
            importlib.import_module("common.storage").download_json_if_exists("stories", "invalid.json")


class TestContracts:
    @pytest.mark.parametrize("payload", [None, [], {}, {"story_id": "../other"}, {"story_id": ""}])
    def test_invalid_story_identity(self, job_env, payload):
        with pytest.raises(ValueError):
            importlib.import_module("common.contracts").validate_trigger(payload, "manifest-job")

    @pytest.mark.parametrize("value", [0, -1, True, "1", 1.5, None])
    def test_chapter_identity_requires_positive_integer(self, job_env, value):
        with pytest.raises(ValueError):
            importlib.import_module("common.contracts").validate_trigger(
                {"story_id": "s1", "chunk_id": value}, "chunk-job")

    @pytest.mark.parametrize("chapters", [[], [{"chapterNumber": 2, "title": "T", "summary": "S"}],
        [{"chapterNumber": 1, "title": " ", "summary": "S"}],
        [{"chapterNumber": True, "title": "T", "summary": "S"}]])
    def test_manifest_must_define_ordered_real_chapters(self, job_env, chapters):
        with pytest.raises(ValueError):
            importlib.import_module("common.contracts").validate_manifest(
                {"storyId": "s1", "chapters": chapters}, "s1")

    def test_cefr_guidelines(self, job_env):
        worker = job_env.modules["chunk_jobs"]
        assert worker.get_cefr_guidelines("A1")
        assert worker.get_cefr_guidelines("A1") != worker.get_cefr_guidelines("C1")
        assert worker.get_cefr_guidelines("unknown") == worker.get_cefr_guidelines("B1")


class TestLease:
    def test_renewal_keeps_long_work_claimed(self, job_env):
        path = job_env.trigger("chunk-job", chunk_id=1)
        lease = importlib.import_module("common.triggers").TriggerLease(job_env.storage.get_blob_client(blob=path))
        with patch.object(lease.stop, "wait", side_effect=[False, False, True]):
            lease._renew()
        assert lease.lease.renewals == 2
        lease.check()
        lease.lease.release()

    def test_failed_renewal_is_reported(self, job_env):
        path = job_env.trigger("chunk-job", chunk_id=1)
        lease = importlib.import_module("common.triggers").TriggerLease(job_env.storage.get_blob_client(blob=path))
        with patch.object(lease.stop, "wait", return_value=False):
            with patch.object(lease.lease, "renew", side_effect=pipeline.StorageError("lost lease", 412)):
                lease._renew()
        with pytest.raises(RuntimeError, match="Lost trigger lease"):
            lease.check()
        lease.lease.release()

    def test_missing_configuration_fails_explicitly(self, job_env, monkeypatch):
        monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING")
        with pytest.raises(RuntimeError, match="not set"):
            job_env.modules["chunk_poller"].main()

    @pytest.mark.parametrize("name", ["manifest_poller", "chunk_poller", "orchestrator_poller", "final_assembly_poller"])
    def test_no_triggers_is_successful_noop(self, job_env, name):
        assert job_env.modules[name].main() == 0

    def test_enqueue_uses_stable_name_without_overwriting_an_existing_claim(self, job_env):
        triggers = importlib.import_module("common.triggers")
        triggers.enqueue("chunk-job", "story_a", "batch", chunk_id=1)
        path = "triggers/chunk-job-scheduled/batch.json"
        lease = job_env.storage.get_blob_client(blob=path).acquire_lease()
        original = job_env.storage.data[path]
        triggers.enqueue("chunk-job", "story_a", "batch", chunk_id=1)
        assert job_env.storage.data[path] == original
        assert job_env.storage.leases[path] is lease
        lease.release()

    def test_conflicting_dispatch_is_not_acknowledged_as_success(self, job_env):
        triggers = importlib.import_module("common.triggers")
        triggers.enqueue("chunk-job", "story_a", "batch", chunk_id=1)
        with pytest.raises(ValueError, match="Conflicting"):
            triggers.enqueue("chunk-job", "story_a", "batch", chunk_id=2)
