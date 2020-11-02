from __future__ import division, print_function

from typing import Generator

import sys

from lxml import etree as ET
from lxml.etree import XMLSyntaxError

from .extracted_text import ExtractedText, normalize_sbb
from .reading_order import  extract_regions_by_order_strategy


def alto_namespace(tree: ET.ElementTree) -> str:
    """Return the ALTO namespace used in the given ElementTree.

    This relies on the assumption that, in any given ALTO file, the root element has the local name "alto". We do not
    check if the files uses any valid ALTO namespace.
    """
    root_name = ET.QName(tree.getroot().tag)
    if root_name.localname == 'alto':
        return root_name.namespace
    else:
        raise ValueError('Not an ALTO tree')


def alto_extract_lines(tree: ET.ElementTree) -> Generator[ExtractedText, None, None]:
    nsmap = {'alto': alto_namespace(tree)}
    for line in tree.iterfind('.//alto:TextLine', namespaces=nsmap):
        line_id = line.attrib.get('ID')
        line_text = ' '.join(string.attrib.get('CONTENT') for string in line.iterfind('alto:String', namespaces=nsmap))
        yield ExtractedText(line_id, None, None, normalize_sbb(line_text))
        # FIXME hardcoded SBB normalization


def alto_extract(tree: ET.ElementTree()) -> ExtractedText:
    """Extract text from the given ALTO ElementTree."""
    return ExtractedText(None, list(alto_extract_lines(tree)), '\n', None)


def alto_text(tree):
    return alto_extract(tree).text


def page_namespace(tree):
    """Return the PAGE content namespace used in the given ElementTree.

    This relies on the assumption that, in any given PAGE content file, the root element has the local name "PcGts". We
    do not check if the files uses any valid PAGE namespace.
    """
    root_name = ET.QName(tree.getroot().tag)
    if root_name.localname == 'PcGts':
        return root_name.namespace
    else:
        raise ValueError('Not a PAGE tree')


def page_extract(tree, *, textequiv_level='region', **kwargs):
    """Extract text from the given PAGE content ElementTree."""

    nsmap = {'page': page_namespace(tree)}

    regions = extract_regions_by_order_strategy(tree, nsmap, **kwargs)
    region_texts = [ExtractedText.from_text_segment(region, nsmap, textequiv_level=textequiv_level) for region in regions]
    region_texts = filter(lambda r: r.text != '', region_texts)
    return ExtractedText(None, region_texts, '\n', None)


def page_text(tree, *, textequiv_level='region', **kwargs):
    return page_extract(tree, textequiv_level=textequiv_level, **kwargs).text


def plain_extract(filename):
    with open(filename, 'r') as f:
        return ExtractedText(
                None,
                [ExtractedText('line %d' % no, None, None, line) for no, line in enumerate(f.readlines())],
                '\n',
                None
        )


def plain_text(filename):
    return plain_extract(filename).text


def extract(filename, *, textequiv_level='region', **kwargs):
    """Extract the text from the given file.

    Supports PAGE, ALTO and falls back to plain text.
    """
    try:
        tree = ET.parse(filename)
    except XMLSyntaxError:
        return plain_extract(filename)
    try:
        return page_extract(tree, textequiv_level=textequiv_level, **kwargs)
    except ValueError:
        return alto_extract(tree)


def text(filename):
    return extract(filename).text


if __name__ == '__main__':
    print(text(sys.argv[1]))
