from __future__ import annotations

import hashlib
import json
from urllib.parse import quote


def build_seed_url(lng: float, lat: float) -> str:
    return f"https://mapsv0.bdimg.com/?qt=qsdata&x={lng}&y={lat}"


def build_metadata_url(panoid: str) -> str:
    return f"https://mapsv0.bdimg.com/?qt=sdata&sid={panoid}"


def build_mock_seed_data(point_index: int, lng: float, lat: float) -> dict:
    digest = hashlib.sha1(f"{point_index}:{lng}:{lat}".encode("utf-8")).hexdigest()[:16]
    return {
        "result": "ok",
        "panoid": f"mock_{digest}",
        "source": {"point_index": point_index, "lng": lng, "lat": lat},
    }


def build_mock_metadata_data(panoid: str, lng: float, lat: float) -> dict:
    return {
        "result": "ok",
        "panoid": panoid,
        "location": {"lng": lng, "lat": lat},
        "capture_date": "2026-01",
        "provider": "baidu",
    }


def data_url(payload: dict) -> str:
    encoded = quote(json.dumps(payload, ensure_ascii=False))
    return f"data:application/json,{encoded}"


def extract_panoid_from_seed(data: dict) -> str | None:
    for key in ("panoid", "Panoid", "PanoID", "sid", "SID"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return _find_string_by_key(data, {"panoid", "Panoid", "PanoID", "sid", "SID"})


def extract_pano_lng(data: dict) -> float | None:
    return _first_float(data, ["lng", "lon", "longitude", "X"])


def extract_pano_lat(data: dict) -> float | None:
    return _first_float(data, ["lat", "latitude", "Y"])


def extract_capture_date(data: dict) -> str | None:
    value = _find_string_by_key(data, {"capture_date", "CaptureDate", "date", "TimeLine"})
    return value


def _first_float(data: dict, names: list[str]) -> float | None:
    for name in names:
        value = _find_value_by_key(data, name)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _find_string_by_key(value, keys: set[str]) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and isinstance(child, (str, int)):
                return str(child)
            found = _find_string_by_key(child, keys)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_string_by_key(child, keys)
            if found:
                return found
    return None


def _find_value_by_key(value, target: str):
    if isinstance(value, dict):
        if target in value:
            return value[target]
        lowered = target.lower()
        for key, child in value.items():
            if key.lower() == lowered:
                return child
            found = _find_value_by_key(child, target)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_value_by_key(child, target)
            if found is not None:
                return found
    return None

