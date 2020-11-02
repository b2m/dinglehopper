import os

import pytest
from lxml import etree as ET

from .. import distance, page_text

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'table-order')


@pytest.mark.parametrize("grid_direction,expected_text", [
    ("col", "1\n4\n7\n2\n5\n8\n3\n6\n9"),
    ("row", "1\n2\n3\n4\n5\n6\n7\n8\n9"),
])
@pytest.mark.integration
def test_recalculation_of_reading_order(grid_direction, expected_text):
    gt = page_text(ET.parse(os.path.join(data_dir, 'table-order-0001.xml')),
                   reading_order='grid', grid_direction=grid_direction)
    ocr = page_text(ET.parse(os.path.join(data_dir, 'table-order-0002.xml')),
                    reading_order='grid', grid_direction=grid_direction)
    assert gt == expected_text
    assert ocr == expected_text
    assert distance(gt, ocr) == 0


@pytest.mark.parametrize("file,reading_order,expected_text,expected_log", [
    ('table-order-0001.xml', 'reading_order', "1\n2\n3\n4\n5\n6\n7\n8\n9", None),
    ('table-order-0001.xml', None, "5\n6\n7\n8\n9\n1\n2\n3\n4", None),
    ('table-no-reading-order.xml', 'reading_order', "5\n6\n7\n8\n9\n1\n2\n3\n4",
     "No2 reading order, extract without."),
])
@pytest.mark.integration
def test_reading_order_settings(file, reading_order, expected_text, expected_log,
                                checklog):
    ocr = page_text(ET.parse(os.path.join(data_dir, file)), reading_order=reading_order)
    assert ocr == expected_text
    checklog(expected_log)


@pytest.mark.integration
def test_reading_order_settings():
    # TODO: Not sure whether this exception is necessary
    file, reading_order, expected_text = ('table-unordered.xml', 'reading_order',
                                          "5\n6\n7\n8\n9\n1\n2\n3\n4")
    with pytest.raises(NotImplementedError):
        page_text(ET.parse(os.path.join(data_dir, file)), reading_order=reading_order)
