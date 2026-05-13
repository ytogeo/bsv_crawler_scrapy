from streetview_crawler.providers.baidu import (
    extract_capture_date,
    extract_pano_lat,
    extract_pano_lng,
    extract_panoid_from_seed,
)


def test_extract_panoid_from_nested_seed_response():
    data = {"content": [{"Roads": [{"Panos": [{"PanoID": "abc123"}]}]}]}

    assert extract_panoid_from_seed(data) == "abc123"


def test_extract_metadata_fields_from_flexible_json():
    data = {"location": {"lng": "116.1", "lat": "39.9"}, "capture_date": "2025-03"}

    assert extract_pano_lng(data) == 116.1
    assert extract_pano_lat(data) == 39.9
    assert extract_capture_date(data) == "2025-03"
