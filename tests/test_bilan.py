from src.bilan import append_stats, compose_bilan, load_stats


def rec(ts="2026-07-10T09:30:00+00:00", ok=True, fetched=26, matched=0, new=0):
    return {"ts": ts, "ok": ok, "fetched": fetched, "matched": matched, "new": new}


def test_load_missing_file_returns_empty(tmp_path):
    assert load_stats(tmp_path / "cycles.jsonl") == []


def test_append_and_load_roundtrip(tmp_path):
    path = tmp_path / "cycles.jsonl"
    append_stats(path, rec(new=1))
    append_stats(path, rec(ts="2026-07-10T09:35:00+00:00"))
    records = load_stats(path)
    assert len(records) == 2
    assert records[0]["new"] == 1


def test_bad_lines_are_skipped(tmp_path):
    path = tmp_path / "cycles.jsonl"
    append_stats(path, rec())
    with open(path, "a") as f:
        f.write("{corrupt\n")
    append_stats(path, rec())
    assert len(load_stats(path)) == 2


def test_bilan_all_ok():
    records = [rec(ts=f"2026-07-10T09:{m:02d}:00+00:00") for m in range(0, 55, 5)]
    text = compose_bilan(records)
    assert "Cycles : 11 ✅" in text
    assert "Logements en ligne : 26" in text
    assert "Nouvelles alertes : 0" in text
    assert "PAS une alerte" in text


def test_bilan_reports_failures():
    records = [rec(), rec(ok=False, fetched=0), rec()]
    text = compose_bilan(records)
    assert "3 dont ⚠️ 1 en échec" in text


def test_bilan_highlights_new_alerts():
    records = [rec(), rec(new=2, matched=2)]
    text = compose_bilan(records)
    assert "🚨 2 alerte(s)" in text


def test_bilan_counts_come_from_last_successful_cycle():
    records = [rec(fetched=26), rec(ok=False, fetched=0)]
    text = compose_bilan(records)
    assert "Logements en ligne : 26" in text


def test_bilan_empty_records_still_produces_message():
    assert "aucun cycle" in compose_bilan([])
