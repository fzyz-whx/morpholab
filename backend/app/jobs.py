"""Persistent local queue. Only the separately locked worker executes jobs."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    MetaData,
    String,
    Table,
    case,
    create_engine,
    select,
    update,
)

from backend.app.assets import image_assets
from backend.app.data import DataError


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                # Windows readers can briefly deny FILE_SHARE_DELETE to the target.
                if attempt == 5:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass  # A disposable cache temp must not mask the original write exception.


def worker_ready(directory: Path) -> bool:
    try:
        stamp = json.loads((directory / "worker-status.json").read_text(encoding="utf-8"))
        age = (datetime.now(UTC) - datetime.fromisoformat(stamp["heartbeat_utc"])).total_seconds()
        return stamp["status"] == "ready" and 0 <= age < 5
    except (OSError, ValueError, KeyError, TypeError):
        return False


def job_id(value: str) -> str:
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError) as exc:
        raise DataError("JOB_NOT_FOUND", "Job does not exist.", 404) from exc
    return value


class JobQueue:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            "sqlite:///" + (self.directory / "jobs.sqlite3").as_posix(),
            connect_args={"check_same_thread": False, "timeout": 15},
        )
        metadata = MetaData()
        self.jobs = Table(
            "jobs",
            metadata,
            Column("id", String, primary_key=True),
            Column("status", String, nullable=False),
            Column("request", JSON, nullable=False),
            Column("pinned", JSON, nullable=False),
            Column("created_at_utc", String, nullable=False),
            Column("updated_at_utc", String, nullable=False),
            Column("cancel_requested", Boolean, nullable=False),
            Column("error", JSON),
        )
        metadata.create_all(self.engine)

    def public(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in row.items() if key != "pinned"} | {
            "result_available": row["status"] == "succeeded"
        }

    def get(self, identifier: str) -> dict[str, Any]:
        identifier = job_id(identifier)
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(self.jobs).where(self.jobs.c.id == identifier))
                .mappings()
                .first()
            )
        if row is None:
            raise DataError("JOB_NOT_FOUND", "Job does not exist.", 404)
        return dict(row)

    def submit(self, request: dict[str, Any], pinned: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "status": "queued",
            "request": request,
            "pinned": pinned,
            "created_at_utc": now(),
            "updated_at_utc": now(),
            "cancel_requested": False,
            "error": None,
        }
        with self.engine.begin() as connection:
            connection.execute(self.jobs.insert().values(**row))
        return self.public(row)

    def list(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(self.jobs).order_by(self.jobs.c.created_at_utc.desc()).limit(100)
                )
                .mappings()
                .all()
            )
        return [self.public(dict(row)) for row in rows]

    def cancel(self, identifier: str) -> dict[str, Any]:
        self.get(identifier)
        with self.engine.begin() as connection:
            connection.execute(
                update(self.jobs)
                .where(self.jobs.c.id == identifier, self.jobs.c.status == "queued")
                .values(status="cancelled", cancel_requested=True, updated_at_utc=now())
            )
            connection.execute(
                update(self.jobs)
                .where(self.jobs.c.id == identifier, self.jobs.c.status == "running")
                .values(cancel_requested=True, updated_at_utc=now())
            )
        return self.public(self.get(identifier))

    def recover(self) -> None:
        """Called only after obtaining the exclusive worker lock; replay interrupted jobs."""
        with self.engine.begin() as connection:
            for cancelled in (False, True):
                connection.execute(
                    update(self.jobs)
                    .where(
                        self.jobs.c.status == "running", self.jobs.c.cancel_requested == cancelled
                    )
                    .values(status="cancelled" if cancelled else "queued", updated_at_utc=now())
                )

    def claim(self) -> dict[str, Any] | None:
        with self.engine.begin() as connection:
            identifier = connection.execute(
                select(self.jobs.c.id)
                .where(
                    self.jobs.c.status == "queued",
                    self.jobs.c.cancel_requested == False,  # noqa: E712
                )
                .order_by(self.jobs.c.created_at_utc)
                .limit(1)
            ).scalar()
            if identifier is None:
                return None
            result = connection.execute(
                update(self.jobs)
                .where(
                    self.jobs.c.id == identifier,
                    self.jobs.c.status == "queued",
                    self.jobs.c.cancel_requested == False,  # noqa: E712
                )
                .values(status="running", updated_at_utc=now())
            )
            if result.rowcount != 1:
                return None
        return self.get(identifier)

    def finish(self, identifier: str, status: str, error: dict[str, Any] | None = None) -> None:
        if status not in {"succeeded", "failed", "cancelled"}:
            raise ValueError("Invalid terminal job status")
        with self.engine.begin() as connection:
            # Cancellation wins a race with inference completion.
            connection.execute(
                update(self.jobs)
                .where(self.jobs.c.id == identifier)
                .values(
                    status=case((self.jobs.c.cancel_requested, "cancelled"), else_=status),
                    error=error,
                    updated_at_utc=now(),
                )
            )

    def result_path(self, identifier: str) -> Path:
        return self.directory / "results" / (job_id(identifier) + ".json")

    def result(self, identifier: str) -> dict[str, Any]:
        row = self.get(identifier)
        if row["status"] != "succeeded":
            raise DataError("RESULT_NOT_READY", "Job has no successful result.", 409)
        try:
            result = json.loads(self.result_path(identifier).read_text(encoding="utf-8"))
            return image_assets(result, self.directory / "results", identifier)
        except (OSError, ValueError) as exc:
            raise DataError("RESULT_UNAVAILABLE", "Saved job result is unavailable.") from exc


class WorkerLock:
    """OS advisory lock is released even if a worker process crashes."""

    def __init__(self, directory: Path):
        self.path = directory / "worker.lock"
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+b")
        self.stream.seek(0)
        self.stream.write(b"0")
        self.stream.flush()
        self.stream.seek(0)
        try:
            if __import__("os").name == "nt":
                import msvcrt

                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.stream.close()
            raise RuntimeError("Another worker already owns this application queue") from exc
        return self

    def __exit__(self, *args):
        if self.stream:
            self.stream.close()
