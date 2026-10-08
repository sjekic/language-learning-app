"""Consume chunk-job triggers with one acknowledgement owner."""
import os
from common.triggers import run_pending


def main():
    import chunk_jobs
    return run_pending("chunk-job", chunk_jobs.main, replica_index=int(os.getenv("JOB_COMPLETION_INDEX", "0")))


if __name__ == "__main__":
    main()
