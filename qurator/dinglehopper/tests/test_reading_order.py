from typing import Dict

import pytest
from lxml import etree as ET

from ..reading_order import get_extraction_strategy, extract_regions_with_reading_order, \
    extract_regions_without_reading_order, extract_regions_grid, extract_coords, \
    extract_img_dim, extract_top_left, Point, Dimension, map_point_to_grid


@pytest.mark.parametrize("strategy_key,expected,expected_log", [
    (None, extract_regions_without_reading_order, None),
    ('reading_order', extract_regions_with_reading_order, None),
    ('grid', extract_regions_grid, None),
    ('unknown_key', extract_regions_with_reading_order,
     "Unknown reading order extraction strategy"),
])
def test_get_extraction_strategy(strategy_key, expected, expected_log, logcheck):
    strategy = get_extraction_strategy(strategy_key)

    assert strategy == expected
    assert logcheck(expected_log)


@pytest.fixture
def expected_img_dim() -> Dimension:
    return Dimension(width=1200, height=800)


@pytest.fixture
def expected_coords() -> Dict[str, str]:
    return {
        "r0": "300,450 300,400 350,400 350,450",
        "r1": "100,650 100,600 150,600 150,650"
    }


@pytest.fixture
def xml_coords(xml_ns, expected_coords, expected_img_dim):
    xml = "<?xml version=\"1.0\"?>"
    xml += "<PcGts xmlns=\"{0}\">".format(xml_ns)
    xml += "<Page imageFilename=\"0001.png\""
    xml += " imageHeight=\"{0}\" imageWidth=\"{1}\">".format(
        expected_img_dim.height, expected_img_dim.width)
    for key, value in expected_coords.items():
        xml += "<TextRegion id=\"{0}\">.format(key)".format(key)
        xml += "<Coords points=\"{0}\"/></TextRegion>".format(value)
    xml += "</Page></PcGts>"
    return ET.fromstring(xml)


def test_extract_coords(xml_coords, xml_ns_map, expected_coords):
    coords = extract_coords(xml_coords, xml_ns_map)
    assert coords == expected_coords


def test_extract_img_dim(xml_coords, xml_ns_map, expected_img_dim):
    img_dim = extract_img_dim(xml_coords, xml_ns_map)
    assert img_dim == expected_img_dim


def test_extract_top_left(expected_coords):
    top_left = extract_top_left(expected_coords['r0'])
    assert top_left == Point(x=300, y=400)

    top_left = extract_top_left(expected_coords['r1'])
    assert top_left == Point(x=100, y=600)


@pytest.mark.parametrize("w,h,x,y,size,expected_id,expected_log", [
    (35, 20, -10, -10, 10, 1, "Negative coordinates not expected, set to 0."),
    (35, 20, 0, 0, 10, 1, None),
    (35, 20, 15, 12, 10, 6, None),
    (35, 20, 35, 20, 10, 8, None),
    (35, 20, 70, 40, 10, 8, "Point coordinates bigger than image, set to image size.")
])
def test_map_point_to_grid(w, h, x, y, size, expected_id, expected_log, logcheck):
    img_dim = Dimension(width=w, height=h)
    point = Point(x=x, y=y)
    grid_size = size

    grid_id = map_point_to_grid(img_dim, point, grid_size=grid_size)
    assert grid_id == expected_id
    assert logcheck(expected_log)


def test_map_point_to_grid_exception():
    with pytest.raises(ValueError):
        map_point_to_grid(Dimension(0, 0), Point(0, 0), grid_direction="unknown")


def test_extraction_grid_row(xml_coords, xml_ns_map):
    region_ids = extract_regions_grid(xml_coords, xml_ns_map, grid_direction="row")
    assert region_ids == ["r0", "r1"]

    region_ids = extract_regions_grid(xml_coords, xml_ns_map, grid_direction="col")
    assert region_ids == ["r1", "r0"]

    region_ids = extract_regions_grid(xml_coords, xml_ns_map, grid_direction="col",
                                      grid_size=1000)
    assert region_ids == ["r0", "r1"]
