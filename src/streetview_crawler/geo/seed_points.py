from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SeedPoint:
    point_index: int
    lng: float
    lat: float

    def as_dict(self) -> dict[str, float | int]:
        return {"point_index": self.point_index, "lng": self.lng, "lat": self.lat}


def generate_seed_points(aoi_path: str | Path, interval_m: float) -> list[dict[str, float | int]]:
    polygons = _load_polygons(Path(aoi_path))
    if not polygons:
        return []

    lngs = [lng for polygon in polygons for ring in polygon for lng, _ in ring]
    lats = [lat for polygon in polygons for ring in polygon for _, lat in ring]
    min_lng, max_lng = min(lngs), max(lngs)
    min_lat, max_lat = min(lats), max(lats)

    mid_lat = (min_lat + max_lat) / 2
    lat_step = interval_m / 111_320.0
    lng_step = interval_m / (111_320.0 * max(math.cos(math.radians(mid_lat)), 0.01))

    points: list[SeedPoint] = []
    index = 0
    lat = min_lat
    row = 0
    while lat <= max_lat + 1e-12:
        offset = (lng_step / 2) if row % 2 else 0
        lng = min_lng + offset
        while lng <= max_lng + 1e-12:
            if _contains_any(polygons, lng, lat):
                points.append(SeedPoint(index, round(lng, 8), round(lat, 8)))
                index += 1
            lng += lng_step
        row += 1
        lat += lat_step
    return [point.as_dict() for point in points]


def _load_polygons(path: Path) -> list[list[list[tuple[float, float]]]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    geometries: list[dict] = []
    if data.get("type") == "FeatureCollection":
        geometries = [feature["geometry"] for feature in data.get("features", [])]
    elif data.get("type") == "Feature":
        geometries = [data["geometry"]]
    else:
        geometries = [data]

    polygons: list[list[list[tuple[float, float]]]] = []
    for geometry in geometries:
        gtype = geometry.get("type")
        coords = geometry.get("coordinates", [])
        if gtype == "Polygon":
            polygons.append(_normalize_polygon(coords))
        elif gtype == "MultiPolygon":
            polygons.extend(_normalize_polygon(poly) for poly in coords)
    return polygons


def _normalize_polygon(coords: Iterable) -> list[list[tuple[float, float]]]:
    return [[(float(lng), float(lat)) for lng, lat in ring] for ring in coords]


def _contains_any(polygons: list[list[list[tuple[float, float]]]], lng: float, lat: float) -> bool:
    return any(_contains_polygon(polygon, lng, lat) for polygon in polygons)


def _contains_polygon(polygon: list[list[tuple[float, float]]], lng: float, lat: float) -> bool:
    if not polygon or not _point_in_ring(lng, lat, polygon[0]):
        return False
    return not any(_point_in_ring(lng, lat, hole) for hole in polygon[1:])


def _point_in_ring(lng: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if _point_on_segment(lng, lat, xi, yi, xj, yj):
            return True
        intersects = (yi > lat) != (yj > lat)
        if intersects:
            x_intersect = (xj - xi) * (lat - yi) / (yj - yi + 1e-20) + xi
            if lng < x_intersect:
                inside = not inside
        j = i
    return inside


def _point_on_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> bool:
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > 1e-10:
        return False
    dot = (px - ax) * (px - bx) + (py - ay) * (py - by)
    return dot <= 1e-10

