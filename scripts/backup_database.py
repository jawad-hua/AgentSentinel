"""Offline SQLite backup. Stop the API first; do not lose the matching snapshot key."""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from app.config import Settings
from app.worker_lock import worker_lock
from sqlalchemy.engine import make_url


def backup(database_url: str, output: Path) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        raise ValueError("This backup command supports file-backed SQLite only")
    source = Path(url.database).resolve()
    if not source.is_file():
        raise ValueError("Source database does not exist")
    with worker_lock(database_url):
        # Exclusive creation prevents overwriting the only known-good backup.
        with output.open("xb"):
            pass
        output.chmod(0o600)
        try:
            with (
                closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as reader,
                closing(sqlite3.connect(output)) as writer,
            ):
                reader.backup(writer)
                if writer.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup integrity check failed")
        except Exception:
            output.unlink(missing_ok=True)
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        backup(Settings().database_url, args.output)
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        raise SystemExit("Backup failed. Stop the API; check paths and use a new output filename.")
    print("Database backup created and integrity checked. No secrets printed.")
    print("Keep the matching backend .env securely; its snapshot key is required for recovery.")
