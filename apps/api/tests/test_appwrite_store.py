from pathlib import Path

import pytest
from appwrite.exception import AppwriteException

from app import appwrite_store
from app.appwrite_store import AppwriteRunStore
from app.schemas import SyncMap
from tests.fake_appwrite import FakeStorage, FakeTables


class FlakyTables(FakeTables):
    """Drops the connection on the first call of each kind, like Appwrite Cloud sometimes does."""

    def __init__(self) -> None:
        super().__init__()
        self.dropped: set[str] = set()
        self.reads = 0

    def _flaky(self, kind: str) -> None:
        if kind not in self.dropped:
            self.dropped.add(kind)
            raise AppwriteException("Connection aborted.")  # code 0: no HTTP response

    def create_row(self, *args, **kwargs):
        result = super().create_row(*args, **kwargs)
        self._flaky("create")  # the row landed, then the reply was lost
        return result

    def update_row(self, *args, **kwargs):
        self._flaky("update")
        return super().update_row(*args, **kwargs)

    def get_row(self, *args, **kwargs):
        self.reads += 1
        self._flaky("get")
        return super().get_row(*args, **kwargs)


@pytest.fixture
def tables(monkeypatch: pytest.MonkeyPatch) -> FlakyTables:
    monkeypatch.setattr(appwrite_store.time, "sleep", lambda _: None)
    return FlakyTables()


def test_dropped_connections_are_retried(tables: FlakyTables, tmp_path: Path):
    store = AppwriteRunStore(tables, FakeStorage(), cache=tmp_path)  # type: ignore[arg-type]
    meta = store.create("spec.pdf", b"%PDF", "en")
    store.update(meta, stage="planning")
    assert store.get(meta.id).stage == "planning"  # type: ignore[union-attr]
    assert tables.dropped == {"create", "update", "get"}


def test_outputs_are_read_once(tables: FlakyTables, tmp_path: Path):
    writer = AppwriteRunStore(tables, FakeStorage(), cache=tmp_path)  # type: ignore[arg-type]
    writer.save("run_000000000001", "linear", SyncMap(team_id="t"))
    reader = AppwriteRunStore(tables, FakeStorage(), cache=tmp_path)  # type: ignore[arg-type]
    for _ in range(3):
        assert reader.load("run_000000000001", "linear", SyncMap) == SyncMap(team_id="t")
        assert reader.load("run_000000000001", "plan", SyncMap) is None
    assert tables.reads == 3  # one dropped + one retried for "linear", one for "plan"
