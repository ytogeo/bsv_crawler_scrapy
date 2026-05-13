"""
百度街景接口适配模块。

该模块封装百度街景接口的业务细节，包括：
- 构造 seed、metadata 和全景瓦片请求 URL
- 从 seed 响应中提取 panoid
- 从 metadata 响应中提取坐标、拍摄日期等字段

模块本身不直接发起网络请求。Scrapy spider 负责 seed/metadata 请求，
pano 下载流程负责瓦片请求。
"""

from __future__ import annotations


def build_seed_url(lng: float, lat: float) -> str:
    return f"https://mapsv0.bdimg.com/?qt=qsdata&x={lng}&y={lat}"


def build_metadata_url(panoid: str) -> str:
    return f"https://mapsv0.bdimg.com/?qt=sdata&sid={panoid}"


def build_panorama_tile_url(panoid: str, x: int, y: int, zoom: int) -> str:
    return f"https://mapsv0.bdimg.com/?qt=pdata&sid={panoid}&pos={x}_{y}&z={zoom}"


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
    return _find_string_by_key(data, {"capture_date", "CaptureDate", "date", "TimeLine"})


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

