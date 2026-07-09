"""Match accommodations against the target area (Clermont-Ferrand / Aubière).

Only the address and label fields are scanned — never the whole JSON blob.
Rents are stored in cents (e.g. 363000), so a naive full-text search for the
zip code 63000 would false-positive; and residence descriptions/entity names
mention "Clermont" for accommodations that are actually elsewhere (e.g. the
Montluçon residence belongs to the "Clermont Auvergne" CROUS).
"""

from __future__ import annotations

import re
import unicodedata

from .config import TARGET_CITY_KEYWORDS, TARGET_ZIP_CODES

# \b keeps "363000" (a rent in cents) from matching zip 63000.
_ZIP_RE = re.compile(r"\b(" + "|".join(re.escape(z) for z in sorted(TARGET_ZIP_CODES)) + r")\b")


def normalize(text: str) -> str:
    """Lowercase and strip accents: 'AUBIÈRE' -> 'aubiere'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def _searchable_fields(item: dict) -> list[str]:
    residence = item.get("residence") or {}
    fields = [
        residence.get("address"),
        residence.get("label"),
        item.get("label"),
    ]
    return [f for f in fields if f]


def matches_target(item: dict) -> bool:
    """True if the accommodation is in Clermont-Ferrand or Aubière."""
    for field in _searchable_fields(item):
        if _ZIP_RE.search(field):
            return True
        normalized = normalize(field)
        # Substring check against full city names only. Deliberately no bare
        # "clermont": Clermont-l'Hérault (34) and Clermont (60) would match.
        if any(keyword in normalized for keyword in TARGET_CITY_KEYWORDS):
            return True
    return False
