import json

from src.state import diff_new, load_ids, save_ids


def test_load_missing_file_returns_empty(tmp_path):
    assert load_ids(tmp_path / "state.json") == set()


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    save_ids(path, {3, 1, 2})
    assert load_ids(path) == {1, 2, 3}
    # Atomic write leaves no tmp file behind.
    assert list(tmp_path.iterdir()) == [path]


def test_corrupt_file_treated_as_empty(tmp_path, caplog):
    path = tmp_path / "state.json"
    path.write_text("{not valid json!!", encoding="utf-8")
    assert load_ids(path) == set()
    assert "corrupt" in caplog.text


def test_wrong_schema_treated_as_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert load_ids(path) == set()


def test_diff_new_returns_only_unseen(make_item):
    items = [make_item(item_id=1), make_item(item_id=2), make_item(item_id=3)]
    assert [i["id"] for i in diff_new(items, {1, 3})] == [2]


def test_diff_new_first_run_everything_is_new(make_item):
    items = [make_item(item_id=1), make_item(item_id=2)]
    assert len(diff_new(items, set())) == 2


def test_second_run_with_one_added_id(tmp_path, make_item):
    path = tmp_path / "state.json"
    first = [make_item(item_id=10), make_item(item_id=11)]
    save_ids(path, {i["id"] for i in first})

    second = first + [make_item(item_id=12)]
    new = diff_new(second, load_ids(path))
    assert [i["id"] for i in new] == [12]
