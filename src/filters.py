"""Match accommodations against the target area (Clermont-Ferrand / Aubière).

Two independent checks, either one is enough:
1. Text: address/label fields contain a target city name or zip code.
   Only those fields are scanned — never the whole JSON blob. Rents are
   stored in cents (e.g. 363000), so a naive full-text search for the zip
   63000 would false-positive; and residence descriptions/entity names
   mention "Clermont" for accommodations that are actually elsewhere
   (the Montluçon residence belongs to the "Clermont Auvergne" CROUS).
2. Geo: residence.location within radius_km of ISIMA (campus des Cézeaux),
   so spelling variants in addresses can't cause a miss.
"""

from __future__ import annotations

import re
import unicodedata
from math import asin, cos, radians, sin, sqrt

from .config import (
    DEFAULT_RADIUS_KM,
    TARGET_CITY_KEYWORDS,
    TARGET_LAT,
    TARGET_LON,
    TARGET_ZIP_CODES,
)

# \b keeps "363000" (a rent in cents) from matching zip 63000.
_ZIP_RE = re.compile(r"\b(" + "|".join(re.escape(z) for z in sorted(TARGET_ZIP_CODES)) + r")\b")

_EARTH_RADIUS_KM = 6371.0


def normalize(text: str) -> str:
    """Lowercase and strip accents: 'AUBIÈRE' -> 'aubiere'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle (haversine) distance in kilometers."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * asin(sqrt(h))


def distance_to_target(item: dict) -> float | None:
    """Distance from the residence to ISIMA in km, or None if no location."""
    location = (item.get("residence") or {}).get("location") or {}
    lat, lon = location.get("lat"), location.get("lon")
    if lat is None or lon is None:
        return None
    return distance_km(lat, lon, TARGET_LAT, TARGET_LON)


def _searchable_fields(item: dict) -> list[str]:
    residence = item.get("residence") or {}
    fields = [
        residence.get("address"),
        residence.get("label"),
        item.get("label"),
    ]
    return [f for f in fields if f]


def matches_target(item: dict, radius_km: float = DEFAULT_RADIUS_KM) -> bool:
    """True if the accommodation is in Clermont-Ferrand/Aubière or within
    radius_km of ISIMA."""
    for field in _searchable_fields(item):
        if _ZIP_RE.search(field):
            return True
        normalized = normalize(field)
        # Substring check against full city names only. Deliberately no bare
        # "clermont": Clermont-l'Hérault (34) and Clermont (60) would match.
        if any(keyword in normalized for keyword in TARGET_CITY_KEYWORDS):
            return True

    if radius_km > 0:
        distance = distance_to_target(item)
        if distance is not None and distance <= radius_km:
            return True
    return False
