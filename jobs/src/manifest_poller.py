"""Consume manifest-job triggers with one acknowledgement owner."""
from common.triggers import run_pending


def main():
    import manifest
    return run_pending("manifest-job", manifest.main)


if __name__ == "__main__":
    main()
