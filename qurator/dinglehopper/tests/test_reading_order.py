import pytest

from ..reading_order import get_extraction_strategy, extract_regions_with_reading_order, \
    extract_regions_without_reading_order


@pytest.mark.parametrize("strategy_key,expected,expected_log", [
    (None, extract_regions_without_reading_order, None),
    ('reading_order', extract_regions_with_reading_order, None),
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
