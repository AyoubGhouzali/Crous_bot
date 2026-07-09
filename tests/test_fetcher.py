import copy
from unittest.mock import Mock, patch

import pytest
import requests

from src.config import Config
from src.fetcher import FetchError, fetch_all


def make_config(**overrides) -> Config:
    defaults = dict(
        id_tool="47",
        page_size=2,
        page_pause=0.0,
        retry_delays=(0.0, 0.0, 0.0),
        request_timeout=1.0,
    )
    defaults.update(overrides)
    return Config(**defaults)


def response_with_items(items, page_size=2):
    return Mock(
        status_code=200,
        json=Mock(return_value={
            "results": {"total": {"value": 3}, "page": 0, "pageSize": page_size, "items": items},
        }),
    )


def page_items(sample_items, n, start_id=1):
    items = []
    for k in range(n):
        item = copy.deepcopy(sample_items[0])
        item["id"] = start_id + k
        items.append(item)
    return items


def test_happy_path_two_pages(sample_items):
    cfg = make_config()
    full_page = response_with_items(page_items(sample_items, 2, start_id=1))
    partial_page = response_with_items(page_items(sample_items, 1, start_id=3))

    with patch("src.fetcher.requests.post", side_effect=[full_page, partial_page]) as post:
        items = fetch_all(cfg)

    assert [i["id"] for i in items] == [1, 2, 3]
    assert post.call_count == 2
    # Pagination is 1-based in the request payload.
    assert post.call_args_list[0].kwargs["json"]["page"] == 1
    assert post.call_args_list[1].kwargs["json"]["page"] == 2


def test_503_then_success_retries(sample_items):
    cfg = make_config()
    error = Mock(status_code=503)
    ok = response_with_items(page_items(sample_items, 1))

    with patch("src.fetcher.requests.post", side_effect=[error, ok]) as post:
        items = fetch_all(cfg)

    assert len(items) == 1
    assert post.call_count == 2


def test_permanent_failure_raises_fetch_error():
    cfg = make_config()
    with patch(
        "src.fetcher.requests.post",
        side_effect=requests.ConnectionError("connection refused"),
    ) as post:
        with pytest.raises(FetchError):
            fetch_all(cfg)
    assert post.call_count == 3  # one attempt per retry delay


def test_malformed_json_then_success(sample_items):
    cfg = make_config()
    bad = Mock(status_code=200, json=Mock(side_effect=ValueError("bad json")))
    ok = response_with_items(page_items(sample_items, 1))

    with patch("src.fetcher.requests.post", side_effect=[bad, ok]):
        assert len(fetch_all(cfg)) == 1


def test_4xx_fails_immediately_without_retry():
    cfg = make_config()
    with patch("src.fetcher.requests.post", return_value=Mock(status_code=404)) as post:
        with pytest.raises(FetchError, match="ID_TOOL"):
            fetch_all(cfg)
    assert post.call_count == 1
