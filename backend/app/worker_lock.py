"""Prevent two local workers from coordinating repairs against the same SQLite file."""

import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy.engine import make_url


@contextmanager
def worker_lock(database_url: str):
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise RuntimeError("This release requires a file-backed SQLite database and one worker")
    path = Path(url.database).resolve().with_suffix(".worker.lock")
    handle = path.open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("Another AgentSentinel worker holds this database") from None
        yield
    finally:
        # Closing releases the OS lock, including after an interrupted process.
        handle.close()
