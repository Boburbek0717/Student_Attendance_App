"""Development guard: install BEFORE importing app.main. Never reads live data."""
from contextlib import contextmanager
from pathlib import Path
import tempfile


@contextmanager
def isolated_imports():
    from sqlalchemy import event
    from app import database, security

    def deny_live(*args, **kwargs):
        raise RuntimeError("Live database access is forbidden in isolated verification")

    previous = security.SECRET_PATH
    with tempfile.TemporaryDirectory(prefix="sat-factory-secret-") as directory:
        security.SECRET_PATH = Path(directory) / "disposable-secret"
        event.listen(database.engine, "do_connect", deny_live)
        try:
            yield
        finally:
            event.remove(database.engine, "do_connect", deny_live)
            security.SECRET_PATH = previous
