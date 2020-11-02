from typing import Dict

import pytest


@pytest.fixture
def xml_ns() -> str:
    return "http://schema.primaresearch.org/PAGE/gts/pagecontent/2018-07-15"


@pytest.fixture
def xml_ns_map(xml_ns) -> Dict[str, str]:
    return {'page': xml_ns}


@pytest.fixture
def logcheck(caplog):
    def _inner(expected_log):
        if expected_log:
            return expected_log in caplog.text
        else:
            return not caplog.text

    return _inner
