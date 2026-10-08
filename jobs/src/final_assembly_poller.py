"""Consume final-assembly-job triggers with one acknowledgement owner."""
from common.triggers import run_pending


def main():
    import final_assembly_job
    return run_pending("final-assembly-job", final_assembly_job.main)


if __name__ == "__main__":
    main()
