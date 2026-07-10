import json
from datetime import datetime, timedelta, timezone

from src.main import heartbeat_due
from src.state import diff_new, load_state, save_state


def test_load_missing_file_returns_empty(tmp_path):
    state = load_state(tmp_path / "state.json")
    assert state == {"ids": set(), "last_heartbeat": None}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    heartbeat = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    save_state(path, {3, 1, 2}, heartbeat)
    state = load_state(path)
    assert state["ids"] == {1, 2, 3}
    assert state["last_heartbeat"] == heartbeat
    # Atomic write leaves no tmp file behind.
    assert list(tmp_path.iterdir()) == [path]


def test_save_without_heartbeat(tmp_path):
    path = tmp_path / "state.json"
    save_state(path, {1})
    assert load_state(path)["last_heartbeat"] is None


def test_old_format_without_heartbeat_still_loads(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"ids": [4, 5]}), encoding="utf-8")
    state = load_state(path)
    assert state["ids"] == {4, 5}
    assert state["last_heartbeat"] is None


def test_corrupt_file_treated_as_empty(tmp_path, caplog):
    path = tmp_path / "state.json"
    path.write_text("{not valid json!!", encoding="utf-8")
    assert load_state(path)["ids"] == set()
    assert "corrupt" in caplog.text


def test_wrong_schema_treated_as_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert load_state(path)["ids"] == set()


def test_diff_new_returns_only_unseen(make_item):
    items = [make_item(item_id=1), make_item(item_id=2), make_item(item_id=3)]
    assert [i["id"] for i in diff_new(items, {1, 3})] == [2]


def test_diff_new_first_run_everything_is_new(make_item):
    items = [make_item(item_id=1), make_item(item_id=2)]
    assert len(diff_new(items, set())) == 2


def test_second_run_with_one_added_id(tmp_path, make_item):
    path = tmp_path / "state.json"
    first = [make_item(item_id=10), make_item(item_id=11)]
    save_state(path, {i["id"] for i in first})

    second = first + [make_item(item_id=12)]
    new = diff_new(second, load_state(path)["ids"])
    assert [i["id"] for i in new] == [12]


NOW = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)


def test_heartbeat_due_on_first_ever_run():
    assert heartbeat_due(None, NOW, 24)


def test_heartbeat_not_due_before_interval():
    assert not heartbeat_due(NOW - timedelta(hours=23), NOW, 24)


def test_heartbeat_due_after_interval():
    assert heartbeat_due(NOW - timedelta(hours=25), NOW, 24)


def test_heartbeat_disabled_with_zero():
    assert not heartbeat_due(None, NOW, 0)
