from lxml import etree as et

from ocrd_utils import getLogger

LOG = getLogger('processor.OcrdDinglehopperEvaluate')


def extract_regions_by_order_strategy(tree, nsmap, reading_order='reading_order'):
    strategy = get_extraction_strategy(reading_order)
    region_ids = strategy(tree, nsmap)
    regions = [tree.find('.//page:TextRegion[@id="%s"]' % region_id, namespaces=nsmap) for
               region_id in region_ids]
    regions = filter(lambda r: r is not None, regions)
    return regions


def get_extraction_strategy(reading_order):
    strategies = {
        None: extract_regions_without_reading_order,
        "no_reading_order": extract_regions_without_reading_order,
        "reading_order": extract_regions_with_reading_order
    }
    if reading_order not in strategies.keys():
        LOG.error("Unknown reading order extraction strategy %s, using default strategy.",
                  reading_order)
        reading_order = "reading_order"

    return strategies[reading_order]


def extract_regions_with_reading_order(tree, nsmap):
    region_ids = []
    reading_order = tree.find('.//page:ReadingOrder', namespaces=nsmap)
    if reading_order is None:
        LOG.warning("No reading order, extract without.")
        return extract_regions_without_reading_order(tree, nsmap)

    for group in reading_order.iterfind('./*', namespaces=nsmap):
        if et.QName(group.tag).localname != 'OrderedGroup':
            raise NotImplementedError

        region_ref_indexeds = group.findall('./page:RegionRefIndexed', namespaces=nsmap)
        region_ref_indexeds = sorted(region_ref_indexeds,
                                     key=lambda r: int(r.attrib['index']))
        region_ids = [region_ref_indexed.attrib['regionRef'] for region_ref_indexed in
                      region_ref_indexeds]
    return region_ids


def extract_regions_without_reading_order(tree, nsmap):
    region_ids = [r.attrib['id'] for r in
                  tree.iterfind('.//page:TextRegion', namespaces=nsmap)]
    return region_ids
