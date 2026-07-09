import copy
import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "sample_response.json"


@pytest.fixture(scope="session")
def sample_response() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def sample_items(sample_response) -> list[dict]:
    return copy.deepcopy(sample_response["results"]["items"])


@pytest.fixture
def make_item(sample_items):
    """Build a realistic item from the fixture with overridable fields."""

    def _make(item_id=9999, address="1 rue Test 75001 PARIS",
              residence_label="RES TEST", label="T1", rent_min=30000):
        item = copy.deepcopy(sample_items[0])
        item["id"] = item_id
        item["residence"]["address"] = address
        item["residence"]["label"] = residence_label
        item["label"] = label
        for mode in item["occupationModes"]:
            mode["rent"]["min"] = rent_min
            mode["rent"]["max"] = rent_min
        return item

    return _make
