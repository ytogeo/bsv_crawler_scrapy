from PIL import Image

from streetview_crawler.services.image_stitcher import compute_sha256, inspect_image, save_image, stitch_grid


def test_stitch_grid_and_hash():
    tiles = [
        Image.new("RGB", (10, 8), "red"),
        Image.new("RGB", (10, 8), "green"),
        Image.new("RGB", (10, 8), "blue"),
        Image.new("RGB", (10, 8), "white"),
    ]
    image = stitch_grid(tiles, cols=2, rows=2)
    out = __import__("pathlib").Path(__file__).resolve().parents[1] / "data" / "test_outputs" / "pano.jpg"
    save_image(image, out)
    info = inspect_image(out)

    assert info["width"] == 20
    assert info["height"] == 16
    assert len(compute_sha256(out)) == 64
