"""Place search and reverse geocoding via the free Nominatim and Photon services; call only after a user action."""

import asyncio
import math
import time

import httpx
from schemas.api import join_place_name

_USER_AGENT = "CrisisLens-ANLP-Student-Prototype/0.1"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org"
_PHOTON_URL = "https://photon.komoot.io/api"
_CACHE_LIMIT = 256
_PHOTON_CACHE_LIMIT = _CACHE_LIMIT

_Place = dict[str, str | float]


class _Throttle:
    """Keeps requests at least `interval` seconds apart (the public services are for low volume)."""

    def __init__(self, interval: float) -> None:
        self._interval = interval
        self._last = 0.0

    async def wait(self) -> None:
        elapsed = time.monotonic() - self._last
        await asyncio.sleep(max(0.0, self._interval - elapsed))
        self._last = time.monotonic()


# One lock and throttle per service, shared by all its endpoints.
_nominatim_lock = asyncio.Lock()
_nominatim_throttle = _Throttle(1.1)
_photon_lock = asyncio.Lock()
_photon_throttle = _Throttle(1.0)

_reverse_cache: dict[tuple[float, float], dict[str, str]] = {}
_search_cache: dict[str, list[_Place]] = {}
_photon_cache: dict[str, list[_Place]] = {}


def is_valid_point(lat: float, lon: float) -> bool:
    return (
        math.isfinite(lat)
        and math.isfinite(lon)
        and -90 <= lat <= 90
        and -180 <= lon <= 180
    )


async def _nominatim_json(
    endpoint: str, params: dict[str, str | int | float]
) -> object:
    """One throttled Nominatim request; the caller holds _nominatim_lock."""
    await _nominatim_throttle.wait()
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(
            f"{_NOMINATIM_URL}/{endpoint}",
            params=params,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "en"},
        )
        response.raise_for_status()
        return response.json()


async def reverse_geocode(lat: float, lon: float) -> dict[str, str]:
    """Name and place fields for a map pin the user confirmed."""
    if not is_valid_point(lat, lon):
        raise ValueError("Invalid coordinates")

    key = (round(lat, 5), round(lon, 5))

    async with _nominatim_lock:
        if key in _reverse_cache:
            return _reverse_cache[key].copy()

        data = await _nominatim_json(
            "reverse",
            {
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "addressdetails": 1,
                "zoom": 10,
            },
        )
        if not isinstance(data, dict) or data.get("error"):
            raise ValueError("No location details were returned")

        address = data.get("address") or {}
        if not isinstance(address, dict):
            raise TypeError("Unexpected reverse-geocoding address")

        def address_field(*names: str) -> str:
            """The first non-empty string among these address keys."""
            return next(
                (
                    value
                    for name in names
                    if isinstance((value := address.get(name)), str) and value
                ),
                "",
            )

        city = address_field("city", "town", "village", "municipality")
        region = address_field("state", "region")
        country = address_field("country")
        display_name = data.get("display_name")
        result = {
            "location_name": join_place_name(city, region, country)
            or (display_name if isinstance(display_name, str) else ""),
            "city": city,
            "region": region,
            "country": country,
        }
        if len(_reverse_cache) >= _CACHE_LIMIT:
            _reverse_cache.clear()
        _reverse_cache[key] = result
        return result.copy()


async def search_places(query: str) -> list[_Place]:
    """Up to five matches for an explicit search."""
    query = query.strip()
    if len(query) < 2:
        return []

    key = query.casefold()

    async with _nominatim_lock:
        if key in _search_cache:
            return [place.copy() for place in _search_cache[key]]

        data = await _nominatim_json(
            "search", {"q": query, "format": "jsonv2", "limit": 5}
        )
        if not isinstance(data, list):
            raise TypeError("Unexpected location-search response")

        places: list[_Place] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                name = item["display_name"]
                lat = float(item["lat"])
                lon = float(item["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            if isinstance(name, str) and name.strip() and is_valid_point(lat, lon):
                places.append({"name": name, "lat": lat, "lon": lon})

        if len(_search_cache) >= _CACHE_LIMIT:
            _search_cache.clear()
        _search_cache[key] = places
        return [place.copy() for place in places]


def _photon_place(feature: object) -> _Place | None:
    """One Photon feature as a place, or None when it is unusable."""
    if not isinstance(feature, dict):
        return None
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    try:
        lon, lat = float(coordinates[0]), float(coordinates[1])
    except (TypeError, ValueError):
        return None
    if not is_valid_point(lat, lon):
        return None

    parts = [
        properties.get(field).strip()
        for field in ("name", "street", "housenumber", "city", "state", "country")
        if isinstance(properties.get(field), str) and properties[field].strip()
    ]
    if not parts:
        return None
    return {"name": join_place_name(*parts), "lat": lat, "lon": lon}


async def autocomplete_places(query: str) -> list[_Place]:
    """Up to five suggestions for text typed so far (Photon supports search-as-you-type)."""
    query = query.strip()
    if len(query) < 3:
        return []
    key = query.casefold()

    async with _photon_lock:
        if key in _photon_cache:
            return [item.copy() for item in _photon_cache[key]]

        await _photon_throttle.wait()
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(
                _PHOTON_URL,
                # Extra matches, because repeated names are dropped below.
                params={"q": query, "limit": 8, "lang": "en"},
                headers={"User-Agent": _USER_AGENT},
            )
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict):
            raise TypeError("Unexpected Photon response")
        features = payload.get("features")
        if not isinstance(features, list):
            raise TypeError("Unexpected Photon features")

        results: list[_Place] = []
        seen_names: set[str] = set()
        for feature in features:
            if len(results) >= 5:
                break
            place = _photon_place(feature)
            # Photon can return several map objects with the same label.
            if place is None or str(place["name"]).casefold() in seen_names:
                continue
            seen_names.add(str(place["name"]).casefold())
            results.append(place)

        if len(_photon_cache) >= _PHOTON_CACHE_LIMIT:
            _photon_cache.clear()
        _photon_cache[key] = results
        return [item.copy() for item in results]
