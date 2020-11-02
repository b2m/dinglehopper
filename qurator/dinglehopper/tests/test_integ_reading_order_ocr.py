import os

import pytest
from lxml import etree as ET

from .. import distance, page_text

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'table-order')


@pytest.mark.xfail
@pytest.mark.integration
def test_recalculation_of_reading_order():
    expected_text = "1\n2\n3\n4\n5\n6\n7\n8\n9"
    gt = page_text(ET.parse(os.path.join(data_dir, 'table-order-0001.xml')),
                   reading_order='reading_order')
    ocr = page_text(ET.parse(os.path.join(data_dir, 'table-order-0002.xml')),
                    reading_order='reading_order')
    assert gt == expected_text
    assert ocr == expected_text
    assert distance(gt, ocr) == 0


@pytest.mark.parametrize("file,reading_order,expected_text,expected_log", [
    ('table-order-0001.xml', 'reading_order', "1\n2\n3\n4\n5\n6\n7\n8\n9", None),
    ('table-order-0001.xml', None, "5\n6\n7\n8\n9\n1\n2\n3\n4", None),
    ('table-no-reading-order.xml', 'reading_order', "5\n6\n7\n8\n9\n1\n2\n3\n4",
     "No reading order, extract without."),
])
@pytest.mark.integration
def test_reading_order_settings(file, reading_order, expected_text, expected_log, caplog):
    ocr = page_text(ET.parse(os.path.join(data_dir, file)), reading_order=reading_order)
    assert ocr == expected_text
    if expected_log:
        assert expected_log in caplog.text
    else:
        assert not caplog.text


@pytest.mark.integration
def test_reading_order_settings():
    # TODO: Not sure whether this exception is necessary
    file, reading_order, expected_text = ('table-unordered.xml', 'reading_order',
                                          "5\n6\n7\n8\n9\n1\n2\n3\n4")
    with pytest.raises(NotImplementedError):
        page_text(ET.parse(os.path.join(data_dir, file)), reading_order=reading_order)
