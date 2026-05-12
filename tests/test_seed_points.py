from pathlib import Path

from streetview_crawler.geo.seed_points import generate_seed_points


def test_generate_seed_points_from_sample_aoi():
    root = Path(__file__).resolve().parents[1]
    points = generate_seed_points(root / "inputs" / "sample_aoi.geojson", 100)

    assert points
    assert points[0]["point_index"] == 0
    assert {"point_index", "lng", "lat"} <= set(points[0])

