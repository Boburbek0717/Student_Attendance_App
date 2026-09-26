"""Run unittest with a disposable secret and live SQLAlchemy engine blocked."""
from pathlib import Path
import argparse
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.isolated import isolated_imports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", default="test_*.py")
    args = parser.parse_args()
    with isolated_imports():
        # Prove the guard fails closed before discovering any test modules.
        from app.database import engine
        try:
            with engine.connect():
                raise AssertionError("Live connection guard failed")
        except RuntimeError as error:
            if "Live database access is forbidden" not in str(error):
                raise
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=args.pattern)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
