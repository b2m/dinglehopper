from typing import Dict

import pytest
from lxml import etree as ET

from ..reading_order import get_extraction_strategy, extract_regions_with_reading_order, \
    extract_regions_without_reading_order, extract_regions_grid_col, \
    extract_regions_grid_row, extract_coords, extract_img_dim, extract_top_left, Point, \
    Dimension, map_point_to_grid


@pytest.mark.parametrize("strategy_key,expected,expected_log", [
    (None, extract_regions_without_reading_order, None),
    ('reading_order', extract_regions_with_reading_order, None),
    ('grid_col', extract_regions_grid_col, None),
    ('grid_row', extract_regions_grid_row, None),
    ('unknown_key', extract_regions_with_reading_order,
     "Unknown reading order extraction strategy"),
])
def test_get_extraction_strategy(strategy_key, expected, expected_log, caplog):
    strategy = get_extraction_strategy(strategy_key)

    assert strategy == expected
    if expected_log:
        assert expected_log in caplog.text
    else:
        assert not caplog.text


@pytest.fixture
def xml_ns() -> str:
    return "http://schema.primaresearch.org/PAGE/gts/pagecontent/2018-07-15"


@pytest.fixture
def xml_ns_map(xml_ns) -> Dict[str, str]:
    return {'page': xml_ns}


@pytest.fixture
def expected_img_dim() -> Dimension:
    return Dimension(width=1200, height=800)


@pytest.fixture
def expected_coords() -> Dict[str, str]:
    return {
        "r0": "300,450 300,400 350,400 350,450",
        "r1": "500,650 500,600 550,600 550,650"
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
    assert top_left == Point(x=500, y=600)


@pytest.mark.parametrize("width,height,x,y,size,expected_id", [
    (35, 20, -10, -10, 10, 1),
    (35, 20, 0, 0, 10, 1),
    (35, 20, 15, 12, 10, 6),
    (35, 20, 35, 20, 10, 8),
    (35, 20, 70, 40, 10, 8)
])
def test_map_point_to_grid(width, height, x, y, size, expected_id):
    img_dim = Dimension(width=width, height=height)
    point = Point(x=x, y=y)
    grid_size = size

    grid_id = map_point_to_grid(img_dim, point, grid_size=grid_size)
    assert grid_id == expected_id
