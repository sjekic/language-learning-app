"""Consume orchestrator-job triggers with one acknowledgement owner."""
from common.triggers import run_pending


def main():
    import orchestrator
    return run_pending("orchestrator-job", orchestrator.main)


if __name__ == "__main__":
    main()
