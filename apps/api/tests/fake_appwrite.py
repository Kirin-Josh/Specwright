"""In-memory stand-ins for Appwrite's TablesDB and Storage, enough for AppwriteRunStore."""

import json
from types import SimpleNamespace
from typing import Any

from appwrite.exception import AppwriteException
from appwrite.models.row import Row


class FakeTables:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], dict[str, Any]] = {}

    def create_row(self, database_id: str, table_id: str, row_id: str, data: dict[str, Any]):
        if (table_id, row_id) in self.rows:
            raise AppwriteException("row exists", 409)
        self.rows[table_id, row_id] = dict(data)
        return row(row_id, self.rows[table_id, row_id])

    def get_row(self, database_id: str, table_id: str, row_id: str):
        if (table_id, row_id) not in self.rows:
            raise AppwriteException("row not found", 404)
        return row(row_id, self.rows[table_id, row_id])

    def update_row(self, database_id: str, table_id: str, row_id: str, data: dict[str, Any]):
        if (table_id, row_id) not in self.rows:
            raise AppwriteException("row not found", 404)
        self.rows[table_id, row_id].update(data)
        return row(row_id, self.rows[table_id, row_id])

    def list_rows(self, database_id: str, table_id: str, queries: list[str]):
        equal = [q for q in map(json.loads, queries) if q["method"] == "equal"]
        return SimpleNamespace(rows=[
            row(row_id, data)
            for (table, row_id), data in self.rows.items()
            if table == table_id and all(data.get(q["attribute"]) in q["values"] for q in equal)
        ])


def row(row_id: str, data: dict[str, Any]) -> Row[dict[str, Any]]:
    # Built like the SDK builds rows, so columns it would drop are dropped here too.
    return Row.with_data({"$id": row_id, **data})


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def create_file(self, bucket_id: str, file_id: str, file: Any):
        self.files[file_id] = file.data

    def get_file_download(self, bucket_id: str, file_id: str) -> bytes:
        return self.files[file_id]
