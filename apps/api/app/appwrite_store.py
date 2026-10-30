"""Runs stored in Appwrite: the spec in a storage bucket, run metadata in the `runs` table, and
each stage output as JSON text in the `outputs` table (row ID `<run id>.<stage>`). The column
is `json`, not `data`: the SDK reserves `data` for the row payload and drops such a column.

Create the database, tables and bucket once with `uv run python -m app.appwrite_store`.
"""

import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from appwrite.client import Client
from appwrite.exception import AppwriteException
from appwrite.input_file import InputFile
from appwrite.query import Query
from appwrite.services.storage import Storage
from appwrite.services.tables_db import TablesDB
from pydantic import TypeAdapter
from pydantic_core import to_json

from app.config import settings
from app.runs import ACTIVE_STAGES, RUN_ID, RUNS_DIR, SUFFIXES, RunMeta, RunStore, new_run

DATABASE = "specwright"
RUNS = "runs"
OUTPUTS = "outputs"
BUCKET = "specs"
META_FIELDS = ("spec_title", "language", "spec_file", "stage", "message", "created_at")


def client() -> Client:
    if not (settings.appwrite_project_id and settings.appwrite_api_key):
        raise RuntimeError("APPWRITE_PROJECT_ID and APPWRITE_API_KEY must be set")
    return (Client().set_endpoint(settings.appwrite_endpoint)
            .set_project(settings.appwrite_project_id)
            .set_key(settings.appwrite_api_key))


def is_missing(e: AppwriteException) -> bool:
    return e.code == 404


def call[T](fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Call the SDK, retrying when the connection dropped before any HTTP response (code 0).
    Appwrite Cloud sometimes resets a reused connection."""
    for attempt in range(3):
        try:
            return fn(*args, **kwargs)
        except AppwriteException as e:
            if e.code or attempt == 2:
                raise
            time.sleep(0.5 * (attempt + 1))
    raise AssertionError("unreachable")


def create_once(fn: Callable[..., Any], *args: Any) -> None:
    """Create, accepting 409: a retried request may follow one that did land."""
    try:
        call(fn, *args)
    except AppwriteException as e:
        if e.code != 409:
            raise


class AppwriteRunStore(RunStore):
    """Stage outputs are cached in memory once read or written. That is correct while this API
    process is the only writer; a separate worker process (e.g. ARQ) would need it removed.
    Run metadata is always read live, since the progress stream polls it."""

    def __init__(self, tables: TablesDB, storage: Storage, cache: Path = RUNS_DIR):
        self.tables = tables
        self.storage = storage
        self.cache = cache  # local copies of uploaded specs, for ingest
        self._outputs: dict[str, str | None] = {}  # row ID -> JSON, None if not saved yet

    def create(self, file_name: str, data: bytes, language: str) -> RunMeta:
        meta = new_run(file_name, language)
        create_once(self.storage.create_file, BUCKET, meta.id,
                    InputFile.from_bytes(data, meta.spec_file))
        create_once(self.tables.create_row, DATABASE, RUNS, meta.id, self._row(meta))
        return meta

    def get(self, run_id: str) -> RunMeta | None:
        if not RUN_ID.match(run_id):
            return None
        try:
            row = call(self.tables.get_row, DATABASE, RUNS, run_id)
        except AppwriteException as e:
            if is_missing(e):
                return None
            raise
        return RunMeta.model_validate({**row.data, "id": run_id})

    def write_meta(self, meta: RunMeta) -> None:
        call(self.tables.update_row, DATABASE, RUNS, meta.id, self._row(meta))

    def spec_path(self, meta: RunMeta) -> Path:
        path = self.cache / meta.id / meta.spec_file
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(call(self.storage.get_file_download, BUCKET, meta.id))
        return path

    def save(self, run_id: str, name: str, value: Any) -> None:
        row_id = f"{run_id}.{name}"
        text = to_json(value).decode()
        data = {"run_id": run_id, "name": name, "json": text}
        try:
            call(self.tables.update_row, DATABASE, OUTPUTS, row_id, data)
        except AppwriteException as e:
            if not is_missing(e):
                raise
            create_once(self.tables.create_row, DATABASE, OUTPUTS, row_id, data)
        self._outputs[row_id] = text

    def load[T](self, run_id: str, name: str, tp: type[T]) -> T | None:
        row_id = f"{run_id}.{name}"
        if row_id not in self._outputs:
            try:
                self._outputs[row_id] = call(
                    self.tables.get_row, DATABASE, OUTPUTS, row_id).data["json"]
            except AppwriteException as e:
                if not is_missing(e):
                    raise
                self._outputs[row_id] = None
        text = self._outputs[row_id]
        return None if text is None else TypeAdapter(tp).validate_json(text)

    def active_runs(self) -> Iterable[RunMeta]:
        rows = call(self.tables.list_rows, DATABASE, RUNS, [
            Query.equal("stage", sorted(ACTIVE_STAGES)), Query.limit(100)])
        return [RunMeta.model_validate({**r.data, "id": r.id}) for r in rows.rows]

    @staticmethod
    def _row(meta: RunMeta) -> dict[str, Any]:
        return meta.model_dump(mode="json", include=set(META_FIELDS))


def setup(tables: TablesDB, storage: Storage) -> None:
    """Create the database, tables, columns and bucket that don't exist yet. Each is looked up
    first: on the free plan, creating a second database fails with a plan limit, not a 409."""

    def ensure(what: str, get: Callable[[], Any], create: Callable[[], Any]) -> None:
        try:
            get()
            print(f"exists  {what}")
        except AppwriteException as e:
            if not is_missing(e):
                raise
            create()
            print(f"created {what}")

    def column(table: str, key: str, create: Callable[[], Any]) -> None:
        ensure(f"column {table}.{key}", lambda: tables.get_column(DATABASE, table, key), create)

    ensure(f"database {DATABASE}", lambda: tables.get(DATABASE),
           lambda: tables.create(DATABASE, "Specwright"))
    ensure(f"table {RUNS}", lambda: tables.get_table(DATABASE, RUNS),
           lambda: tables.create_table(DATABASE, RUNS, "Runs"))
    for key, size in (("spec_title", 255), ("language", 8), ("spec_file", 32), ("stage", 16)):
        column(RUNS, key, lambda key=key, size=size:
               tables.create_varchar_column(DATABASE, RUNS, key, size, required=True))
    column(RUNS, "message", lambda:
           tables.create_text_column(DATABASE, RUNS, "message", required=False, default=""))
    column(RUNS, "created_at", lambda:
           tables.create_datetime_column(DATABASE, RUNS, "created_at", required=True))
    ensure(f"table {OUTPUTS}", lambda: tables.get_table(DATABASE, OUTPUTS),
           lambda: tables.create_table(DATABASE, OUTPUTS, "Stage outputs"))
    column(OUTPUTS, "run_id", lambda:
           tables.create_varchar_column(DATABASE, OUTPUTS, "run_id", 36, required=True))
    column(OUTPUTS, "name", lambda:
           tables.create_varchar_column(DATABASE, OUTPUTS, "name", 32, required=True))
    column(OUTPUTS, "json", lambda:
           tables.create_mediumtext_column(DATABASE, OUTPUTS, "json", required=True))
    ensure(f"bucket {BUCKET}", lambda: storage.get_bucket(BUCKET), lambda: storage.create_bucket(
        BUCKET, "Specs", maximum_file_size=50_000_000, encryption=True,
        allowed_file_extensions=[s.lstrip(".") for s in sorted(SUFFIXES)]))
    print("columns are created in the background; wait a few seconds before the first run")


if __name__ == "__main__":
    c = client()
    setup(TablesDB(c), Storage(c))
