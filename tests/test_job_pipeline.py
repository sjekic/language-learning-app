"""Offline integration regressions: run the real pollers and workers against fakes."""
import importlib
import io
import json
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class StorageError(Exception):
    def __init__(self, message="storage error", status_code=500):
        super().__init__(message)
        self.status_code = status_code


class ResourceNotFoundError(StorageError):
    def __init__(self, message="missing blob"):
        super().__init__(message, 404)


class MemoryStorage:
    def __init__(self):
        self.data = {}
        self.deleted = []
        self.leases = {}
        self.fail_upload = None

    def put(self, path, value):
        self.data[path] = json.dumps(value).encode()

    def get(self, path):
        return json.loads(self.data[path])

    def get_container_client(self, container):
        return self

    def get_blob_client(self, blob=None, container=None):
        return MemoryBlob(self, blob)

    def list_blobs(self, name_starts_with):
        return [SimpleNamespace(name=name) for name in sorted(self.data)
                if name.startswith(name_starts_with)]


class MemoryBlob:
    def __init__(self, storage, name):
        self.storage, self.name = storage, name

    def download_blob(self, **kwargs):
        if self.name not in self.storage.data:
            raise ResourceNotFoundError()
        return SimpleNamespace(readall=lambda: self.storage.data[self.name])

    def upload_blob(self, data, overwrite=False, **kwargs):
        if self.storage.fail_upload and self.storage.fail_upload in self.name:
            raise StorageError("simulated upload failure")
        if not overwrite and self.name in self.storage.data:
            raise StorageError("already exists", 409)
        self.storage.data[self.name] = data.encode() if isinstance(data, str) else data

    def acquire_lease(self, lease_duration=60):
        if self.name not in self.storage.data:
            raise ResourceNotFoundError()
        if self.name in self.storage.leases:
            raise StorageError("already leased", 409)
        lease = MemoryLease(self)
        self.storage.leases[self.name] = lease
        return lease

    def delete_blob(self, lease=None):
        if self.name not in self.storage.data:
            raise ResourceNotFoundError()
        if self.name in self.storage.leases and lease is not self.storage.leases[self.name]:
            raise StorageError("lease required", 412)
        del self.storage.data[self.name]
        self.storage.deleted.append(self.name)


class MemoryLease:
    def __init__(self, blob):
        self.blob = blob
        self.renewals = 0

    def renew(self):
        self.renewals += 1

    def release(self):
        self.blob.storage.leases.pop(self.blob.name, None)


class FakeLLM:
    def __init__(self):
        self.calls = []
        self.fail_chapter = None
        self.fail_plan = False
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("response_format"):
            if self.fail_plan:
                raise RuntimeError("planner unavailable")
            content = json.dumps({"title": "A learning story", "chapters": [
                {"chapterNumber": n, "title": f"Chapter {n}", "summary": f"Event {n}"}
                for n in range(1, 11)]})
        else:
            number = int(re.search(r"Write Chapter (\d+)", kwargs["messages"][1]["content"]).group(1))
            if number == self.fail_chapter:
                raise RuntimeError("chapter unavailable")
            content = f"**Chapter {number}**\n\nContenido del capítulo {number}."
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class JobPipelineTests(unittest.TestCase):
    def setUp(self):
        output = patch("sys.stdout", new_callable=io.StringIO)
        output.start()
        self.addCleanup(output.stop)
        sleep = patch("time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)
        self.storage = MemoryStorage()
        self.llm = FakeLLM()
        self.module_names = ["manifest", "chunk_jobs", "orchestrator", "final_assembly_job",
                             "manifest_poller", "chunk_poller", "orchestrator_poller", "final_assembly_poller"]
        self.saved_modules = {name: module for name, module in sys.modules.items()
                              if name == "common" or name.startswith("common.") or name in self.module_names}
        for name in self.saved_modules:
            sys.modules.pop(name)
        self.addCleanup(self.restore_modules)
        azure = ModuleType("azure")
        azure_storage = ModuleType("azure.storage")
        azure_blob = ModuleType("azure.storage.blob")
        azure_blob.BlobServiceClient = SimpleNamespace(from_connection_string=lambda value: self.storage)
        azure_core = ModuleType("azure.core")
        exceptions = ModuleType("azure.core.exceptions")
        exceptions.ResourceNotFoundError = ResourceNotFoundError
        exceptions.HttpResponseError = StorageError
        openai = ModuleType("openai")
        openai.OpenAI = lambda **kwargs: self.llm
        self.sdk_patch = patch.dict(sys.modules, {"azure": azure, "azure.storage": azure_storage,
            "azure.storage.blob": azure_blob, "azure.core": azure_core,
            "azure.core.exceptions": exceptions, "openai": openai})
        self.sdk_patch.start()
        self.addCleanup(self.sdk_patch.stop)
        self.path_patch = patch.object(sys, "path", [str(Path(__file__).parents[1] / "jobs" / "src"), *sys.path])
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.env_patch = patch.dict("os.environ", {"AZURE_STORAGE_CONNECTION_STRING": "offline",
            "JOB_COMPLETION_INDEX": "0", "ORCHESTRATOR_MAX_ATTEMPTS": "1", "ORCHESTRATOR_POLL_SECONDS": "0"})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.modules = {name: importlib.import_module(name) for name in self.module_names}

    def restore_modules(self):
        for name in list(sys.modules):
            if name == "common" or name.startswith("common.") or name in self.module_names:
                sys.modules.pop(name)
        sys.modules.update(self.saved_modules)

    def trigger(self, job, story="story_a", trigger_id="t1", **extra):
        path = f"triggers/{job}-scheduled/{trigger_id}.json"
        self.storage.put(path, {"story_id": story, "trigger_id": trigger_id, **extra})
        return path

    def manifest(self, story="story_a", chapters=2):
        value = {"storyId": story, "title": "A story", "language": "Spanish", "readingLevel": "A1",
                 "genre": "adventure", "chapters": [
                     {"chapterNumber": n, "title": f"Chapter {n}", "summary": f"Event {n}"}
                     for n in range(1, chapters + 1)]}
        self.storage.put(f"Users/{story}/manifest.json", value)
        return value

    def chunk(self, number, story="story_a", **overrides):
        value = {"storyId": story, "chunkId": number, "chapterTitle": f"Chapter {number}",
                 "content": f"Content {number}", "status": "completed", **overrides}
        self.storage.put(f"Users/{story}/chunks/chunk_{number}.json", value)

    def run_poller(self, name):
        try:
            self.modules[name].main()
        except (RuntimeError, SystemExit, TimeoutError, ValueError):
            pass  # Assert persistent state, not the exception used by the CLI.

    def test_actual_pipeline_completes_all_ten_chapters(self):
        self.storage.put("Users/story_a/prompt/raw_story_a.json", {
            "userPrompt": "A journey", "language": "Spanish", "genre": "adventure", "readingLevel": "A1"})
        initial = self.trigger("manifest-job")
        self.run_poller("manifest_poller")
        for _ in range(3):
            self.run_poller("chunk_poller")
        self.run_poller("orchestrator_poller")
        self.run_poller("final_assembly_poller")
        path = "Users/story_a/final/story_story_a.json"
        self.assertIn(path, self.storage.data)
        story = self.storage.get(path)
        self.assertEqual(story["totalChapters"], 10)
        self.assertEqual([c["chapterNumber"] for c in story["chapters"]], list(range(1, 11)))
        self.assertEqual(len(self.storage.deleted), len(set(self.storage.deleted)))
        self.assertIn(initial, self.storage.deleted)
        self.assertFalse(any(name.startswith("triggers/") for name in self.storage.data))

    def test_poller_passes_exact_selected_payload_and_acknowledges_once(self):
        first = self.trigger("chunk-job", trigger_id="a", batch_id=1, chapter_start=1, chapter_end=3)
        second = self.trigger("chunk-job", story="story_b", trigger_id="b", chunk_id=7)
        expected = self.storage.get(second)
        with patch.dict("os.environ", {"JOB_COMPLETION_INDEX": "1"}):
            with patch.object(self.modules["chunk_jobs"], "main") as worker:
                self.run_poller("chunk_poller")
                worker.assert_called_once_with(expected)
        self.assertIn(first, self.storage.data)
        self.assertEqual(self.storage.deleted, [second])

    def test_manifest_failure_retains_selected_trigger(self):
        path = self.trigger("manifest-job")
        self.storage.put("Users/story_a/prompt/raw_story_a.json", {})
        self.llm.fail_plan = True
        self.run_poller("manifest_poller")
        self.assertIn(path, self.storage.data)
        self.assertFalse(self.storage.leases)

    def test_manifest_trigger_upload_failure_is_retryable_without_replanning(self):
        path = self.trigger("manifest-job")
        self.storage.put("Users/story_a/prompt/raw_story_a.json", {})
        self.storage.fail_upload = "triggers/chunk-job"
        self.run_poller("manifest_poller")
        self.assertIn(path, self.storage.data)
        self.storage.fail_upload = None
        self.run_poller("manifest_poller")
        self.assertNotIn(path, self.storage.data)
        self.assertEqual(sum(bool(c.get("response_format")) for c in self.llm.calls), 1)
        self.assertEqual(len(self.storage.list_blobs("triggers/chunk-job-scheduled/")), 3)

    def test_failed_batch_retries_only_unfinished_chapters(self):
        self.manifest(chapters=3)
        path = self.trigger("chunk-job", batch_id=1, chapter_start=1, chapter_end=3)
        self.llm.fail_chapter = 2
        self.run_poller("chunk_poller")
        self.assertIn(path, self.storage.data)
        self.assertIn("Users/story_a/chunks/chunk_1.json", self.storage.data)
        self.llm.fail_chapter = None
        self.run_poller("chunk_poller")
        self.assertNotIn(path, self.storage.data)
        chapter_one_calls = [c for c in self.llm.calls if "Write Chapter 1 " in c["messages"][1]["content"]]
        self.assertEqual(len(chapter_one_calls), 1)

    def test_orchestrator_timeout_retains_trigger(self):
        self.manifest()
        path = self.trigger("orchestrator-job", expected_chunks=2)
        with patch("time.sleep"):
            self.run_poller("orchestrator_poller")
        self.assertIn(path, self.storage.data)
        self.assertFalse(self.storage.list_blobs("triggers/final-assembly-job"))

    def test_partial_story_is_never_published(self):
        self.manifest()
        self.chunk(1)
        path = self.trigger("final-assembly-job")
        self.run_poller("final_assembly_poller")
        self.assertIn(path, self.storage.data)
        self.assertNotIn("Users/story_a/final/story_story_a.json", self.storage.data)

    def test_invalid_chapter_identity_or_content_is_never_published(self):
        for invalid in ({"storyId": "another_story"}, {"chunkId": 2}, {"content": "  "}, {"status": "processing"}):
            with self.subTest(invalid=invalid):
                self.manifest(chapters=1)
                self.chunk(1, **invalid)
                path = self.trigger("final-assembly-job")
                self.run_poller("final_assembly_poller")
                self.assertIn(path, self.storage.data)
                self.assertNotIn("Users/story_a/final/story_story_a.json", self.storage.data)

    def test_leased_trigger_is_not_processed_by_a_second_poller(self):
        self.manifest(chapters=1)
        path = self.trigger("chunk-job", chunk_id=1)
        self.storage.get_blob_client(blob=path).acquire_lease()
        self.run_poller("chunk_poller")
        self.assertEqual(self.llm.calls, [])
        self.assertIn(path, self.storage.data)

    def test_legacy_single_chunk_script_invocation_uses_same_acknowledgement(self):
        self.manifest(chapters=1)
        path = "triggers/chunk-job/legacy.json"
        self.storage.put(path, {"story_id": "story_a", "chunk_id": 1})
        self.modules["chunk_jobs"].main()
        self.assertIn("Users/story_a/chunks/chunk_1.json", self.storage.data)
        self.assertEqual(self.storage.deleted, [path])

    def test_overlapping_poller_cannot_run_a_claimed_trigger(self):
        path = self.trigger("chunk-job", chunk_id=1)
        calls = []
        def worker(payload):
            calls.append(payload)
            self.modules["chunk_poller"].main()
        with patch.object(self.modules["chunk_jobs"], "main", side_effect=worker):
            self.modules["chunk_poller"].main()
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.storage.deleted, [path])
        self.assertFalse(self.storage.leases)

    def test_expired_claim_can_be_retried(self):
        self.manifest(chapters=1)
        path = self.trigger("chunk-job", chunk_id=1)
        stale = self.storage.get_blob_client(blob=path).acquire_lease()
        self.modules["chunk_poller"].main()
        self.assertIn(path, self.storage.data)
        stale.release()  # Azure releases a crashed process's finite lease after expiry.
        self.modules["chunk_poller"].main()
        self.assertEqual(self.storage.deleted, [path])

    def test_lease_renewal_failure_prevents_acknowledgement(self):
        path = self.trigger("chunk-job", chunk_id=1)
        triggers = importlib.import_module("common.triggers")
        original_check = triggers.TriggerLease.check
        def lose_lease(claim):
            claim.error = StorageError("renewal failed", 412)
            original_check(claim)
        with patch.object(self.modules["chunk_jobs"], "main"):
            with patch.object(triggers.TriggerLease, "check", lose_lease):
                self.run_poller("chunk_poller")
        self.assertIn(path, self.storage.data)
        self.assertEqual(self.storage.deleted, [])
        self.assertFalse(self.storage.leases)

    def test_invalid_batch_is_retained_without_generating_content(self):
        for invalid in ({"chapter_start": 0, "chapter_end": 2},
                        {"chapter_start": 3, "chapter_end": 1},
                        {"chapter_start": True, "chapter_end": 2},
                        {"chapter_start": 1},
                        {"chapter_start": 1, "chapter_end": 2, "chunk_id": 1}):
            with self.subTest(invalid=invalid):
                path = self.trigger("chunk-job", batch_id=1, **invalid)
                self.run_poller("chunk_poller")
                self.assertIn(path, self.storage.data)
                self.assertFalse(self.llm.calls)

    def test_out_of_manifest_batch_is_retained(self):
        self.manifest(chapters=1)
        path = self.trigger("chunk-job", batch_id=1, chapter_start=1, chapter_end=2)
        self.run_poller("chunk_poller")
        self.assertIn(path, self.storage.data)
        self.assertFalse(self.llm.calls)

    def test_orchestrator_rejects_wrong_chapters_even_when_file_count_matches(self):
        self.manifest(chapters=2)
        self.chunk(1)
        self.chunk(9)
        path = self.trigger("orchestrator-job", expected_chunks=2)
        self.run_poller("orchestrator_poller")
        self.assertIn(path, self.storage.data)
        self.assertFalse(self.storage.list_blobs("triggers/final-assembly-job"))

    def test_dispatch_failure_retains_orchestrator_trigger(self):
        self.manifest(chapters=1)
        self.chunk(1)
        path = self.trigger("orchestrator-job", expected_chunks=1)
        self.storage.fail_upload = "triggers/final-assembly-job"
        self.run_poller("orchestrator_poller")
        self.assertIn(path, self.storage.data)
        self.storage.fail_upload = None
        self.modules["orchestrator_poller"].main()
        self.assertNotIn(path, self.storage.data)

    def test_final_upload_failure_retains_assembly_trigger(self):
        self.manifest(chapters=1)
        self.chunk(1)
        path = self.trigger("final-assembly-job")
        self.storage.fail_upload = "/final/"
        self.run_poller("final_assembly_poller")
        self.assertIn(path, self.storage.data)
        self.storage.fail_upload = None
        self.modules["final_assembly_poller"].main()
        self.assertNotIn(path, self.storage.data)

    def test_completed_output_survives_duplicate_batch_delivery(self):
        self.manifest(chapters=1)
        self.chunk(1)
        path = self.trigger("chunk-job", chunk_id=1)
        self.modules["chunk_poller"].main()
        self.assertEqual(self.storage.deleted, [path])
        self.assertEqual(self.llm.calls, [])
        self.assertEqual(self.storage.get("Users/story_a/chunks/chunk_1.json")["content"], "Content 1")

    def test_invalid_first_trigger_does_not_starve_later_work(self):
        bad = self.trigger("chunk-job", trigger_id="a", chapter_start=0, chapter_end=1, batch_id=1)
        good = self.trigger("chunk-job", trigger_id="b", chunk_id=1)
        self.manifest(chapters=1)
        self.run_poller("chunk_poller")
        self.assertIn(bad, self.storage.data)
        self.assertNotIn(good, self.storage.data)
        self.assertIn("Users/story_a/chunks/chunk_1.json", self.storage.data)

    def test_claimed_first_trigger_does_not_starve_later_work(self):
        busy = self.trigger("chunk-job", trigger_id="a", chunk_id=1)
        good = self.trigger("chunk-job", trigger_id="b", story="story_b", chunk_id=1)
        self.storage.get_blob_client(blob=busy).acquire_lease()
        self.manifest(story="story_b", chapters=1)
        self.modules["chunk_poller"].main()
        self.assertIn(busy, self.storage.data)
        self.assertNotIn(good, self.storage.data)

    def test_lease_loss_during_generation_prevents_output_write(self):
        self.manifest(chapters=1)
        path = self.trigger("chunk-job", chunk_id=1)
        triggers = importlib.import_module("common.triggers")
        claim = triggers.TriggerLease(self.storage.get_blob_client(blob=path))
        original_create = self.llm.create
        def lose_lease(**kwargs):
            response = original_create(**kwargs)
            claim.error = StorageError("renewal failed", 412)
            return response
        with patch.object(triggers, "TriggerLease", return_value=claim):
            with patch.object(self.llm, "create", side_effect=lose_lease):
                self.run_poller("chunk_poller")
        self.assertIn(path, self.storage.data)
        self.assertNotIn("Users/story_a/chunks/chunk_1.json", self.storage.data)

    def test_worker_logs_do_not_break_windows_console(self):
        manifest = self.manifest(chapters=1)
        manifest["chapters"][0]["title"] = "旅行"
        self.storage.put("Users/story_a/manifest.json", manifest)
        path = self.trigger("chunk-job", chunk_id=1)
        output = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        with redirect_stdout(output):
            self.run_poller("chunk_poller")
        self.assertNotIn(path, self.storage.data)


if __name__ == "__main__":
    unittest.main()
