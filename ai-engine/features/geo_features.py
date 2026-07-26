from __future__ import annotations

import math
from datetime import datetime

from features.entity_history import EntityHistoryTracker

# Approximate coordinates for Phase 2's six offices — kept local to this
# module (features/ has no code dependency on attacks/ or utils/network.py,
# only on Phase 2's *data* artifacts) since geo_location strings carry no
# raw lat/lon.
_OFFICE_COORDINATES: dict[str, tuple[float, float]] = {
    "New York, USA": (40.7128, -74.0060),
    "London, United Kingdom": (51.5074, -0.1278),
    "Bangalore, India": (12.9716, 77.5946),
    "Singapore, Singapore": (1.3521, 103.8198),
    "Berlin, Germany": (52.5200, 13.4050),
    "Sydney, Australia": (-33.8688, 151.2093),
}
_EARTH_RADIUS_KM = 6371.0


def _haversine_km(coord_a: tuple[float, float], coord_b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(coord_a[0]), math.radians(coord_a[1])
    lat2, lon2 = math.radians(coord_b[0]), math.radians(coord_b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return _EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


def parse_country(geo_location: str) -> str:
    parts = geo_location.split(", ")
    return parts[-1] if parts else geo_location


def extract_geo_features(
    timestamp: datetime,
    geo_location: str,
    country: str,
    tracker: EntityHistoryTracker,
) -> dict[str, object]:
    geo_velocity_kmh = 0.0
    if (
        tracker.last_geo_location is not None
        and tracker.last_geo_location != geo_location
        and tracker.last_timestamp is not None
        and geo_location in _OFFICE_COORDINATES
        and tracker.last_geo_location in _OFFICE_COORDINATES
    ):
        elapsed_hours = (timestamp - tracker.last_timestamp).total_seconds() / 3600.0
        if elapsed_hours > 0:
            distance_km = _haversine_km(
                _OFFICE_COORDINATES[tracker.last_geo_location], _OFFICE_COORDINATES[geo_location]
            )
            geo_velocity_kmh = distance_km / elapsed_hours

    country_change = tracker.last_country is not None and tracker.last_country != country

    return {
        "geo_novelty": tracker.is_geo_novel(geo_location),
        "geo_velocity_kmh": round(geo_velocity_kmh, 2),
        "country_change": country_change,
        "city_change_frequency": round(tracker.city_change_frequency, 4),
    }