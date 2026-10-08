# Story generation jobs

The blob-backed pipeline runs four stages:

1. `manifest_poller.py` plans ten chapters and dispatches three batches (1–3, 4–7, 8–10).
2. `chunk_poller.py` generates the chapters in its selected batch. Existing valid chapters are reused on retry.
3. `orchestrator_poller.py` waits for every expected chapter, then dispatches assembly.
4. `final_assembly_poller.py` validates all chapters and publishes the final story in manifest order.

All paths below are inside the `stories` container. A story's input is
`Users/<story_id>/prompt/raw_<story_id>.json`; its manifest is
`Users/<story_id>/manifest.json`; chapters are
`Users/<story_id>/chunks/chunk_<number>.json`; the completed story is
`Users/<story_id>/final/story_<story_id>.json`.

## Trigger contract

Pollers consume `triggers/<job>-scheduled/*.json` and the legacy
`triggers/<job>/*.json` folders. Jobs are `manifest-job`, `chunk-job`,
`orchestrator-job`, and `final-assembly-job`.

Every payload requires a nonempty `story_id` containing only letters, digits,
underscores, and hyphens. New dispatches include `trigger_id` and `job_name`;
legacy triggers without these metadata fields remain accepted. A chunk trigger
uses either a positive integer `chunk_id` or a batch:

```json
{
  "story_id": "story_example",
  "trigger_id": "story_example-batch-1",
  "job_name": "chunk-job",
  "batch_id": 1,
  "chapter_start": 1,
  "chapter_end": 3
}
```

Batch fields must be positive integers, ordered, and inside the manifest.
Mixing `chunk_id` with batch fields is rejected. An orchestrator trigger may
include `expected_chunks`; when present, it must equal the manifest count.
Chapter numbers in a manifest must be consecutive starting at 1, with nonempty
titles and summaries. Generated plans must have exactly ten chapters.

## Ownership, retries, and completion

`common/triggers.py` is the only component that selects and acknowledges
triggers. It acquires a 60-second Azure blob lease, renews it every 20 seconds,
validates the selected JSON, and passes that exact payload to the worker.
Workers never independently select or delete triggers. A trigger is deleted
with its lease only after the worker succeeds. Errors, invalid inputs, failed
uploads, and orchestrator timeouts retain it and produce a nonzero job exit.
Leases are released on error; a crashed process's lease expires so work can be
retried. Known renewal failures stop subsequent generation calls, writes, and
dispatches and prevent acknowledgement.

Chunk replicas use `JOB_COMPLETION_INDEX` as a rotation hint, then scan past
busy or failed triggers until one batch succeeds. Other pollers process the
available triggers. A malformed retained trigger does not block later work.
Invalid triggers need operator correction or removal; there is no automatic
dead-letter queue in this change.

Manifest retries reuse the persisted plan. Downstream trigger names are stable
per story and stage, are created without overwriting, and existing payloads
must match the intended dispatch. A batch retry reuses valid completed chapter
blobs. If a downstream trigger was consumed before its parent retried, it may
be dispatched again; the same output paths and chapter checks make this safe
for normal retries.

Assembly requires every expected chapter with matching `storyId`/`chunkId`,
`status: completed`, and nonempty text. Missing, malformed, empty, or mismatched
chapters prevent final publication. Extra filenames never satisfy missing
chapters. The orchestrator performs the same checks before dispatching assembly.

Delivery is **at least once**. A crash after an LLM response but before storage
can repeat the paid call. A lease cannot atomically cancel an in-flight LLM or
storage request; lease-loss races and independently created duplicate triggers
can still overlap work. This is not an exactly-once execution guarantee.

## Running locally

Install the repository's development dependencies and set
`AZURE_STORAGE_CONNECTION_STRING` and `OPENAI_API_KEY` before using real workers.
From the repository root, poll a stage with, for example:

```powershell
.venv/Scripts/python.exe jobs/src/manifest_poller.py
.venv/Scripts/python.exe jobs/src/chunk_poller.py
.venv/Scripts/python.exe jobs/src/orchestrator_poller.py
.venv/Scripts/python.exe jobs/src/final_assembly_poller.py
```

Invoking `manifest.py`, `chunk_jobs.py`, `orchestrator.py`, or
`final_assembly_job.py` directly remains supported: with no payload argument,
each delegates to its poller and uses the same ownership/acknowledgement path.
There is no reliance on mutable `STORY_ID`/`CHUNK_ID` environment variables.

The orchestrator defaults to 60 checks, 10 seconds apart. Set
`ORCHESTRATOR_MAX_ATTEMPTS` and `ORCHESTRATOR_POLL_SECONDS` to adjust this window.
A timeout leaves work available for a later scheduled invocation.

## Offline verification

These tests run the actual pollers and workers with deterministic in-memory
storage and LLM adapters. They make no cloud calls and require no credentials:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_jobs.py tests/test_job_pipeline.py -q --no-cov -o addopts=
```

The integration regression also runs with Python's standard library alone:

```powershell
python -B -m unittest discover -s tests -p test_job_pipeline.py
```

Coverage includes complete ten-chapter generation, exact payload delivery,
batch and legacy triggers, retry retention, partial-batch reuse, lease
contention/renewal/loss, progress past bad or busy triggers, dispatch and final
upload failures, and rejection of incomplete or invalid final stories. The
storage fake verifies the intended lease calls; it does not replace a staging
smoke test of Azure's lease expiry and network-failure behavior.
