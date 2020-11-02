import itertools as it
import math
from collections import namedtuple, defaultdict
from typing import Dict

from lxml import etree as ET
from ocrd_utils import getLogger

LOG = getLogger('processor.OcrdDinglehopperEvaluate')

Point = namedtuple('Point', ['x', 'y'])
Dimension = namedtuple('Dimension', ['height', 'width'])


def extract_regions_by_order_strategy(tree, nsmap, reading_order='reading_order',
                                      **kwargs):
    """Extract the regions from the xml structure based on a reading order strategy."""
    strategy = get_extraction_strategy(reading_order)
    region_ids = strategy(tree, nsmap, **kwargs)
    regions = [tree.find('.//page:TextRegion[@id="%s"]' % region_id, namespaces=nsmap)
               for region_id in region_ids]
    regions = filter(lambda r: r is not None, regions)
    return regions


def get_extraction_strategy(reading_order):
    """Map a reading order strategy string to the corresponding function."""
    strategies = {
        None: extract_regions_without_reading_order,
        "grid": extract_regions_grid,
        "reading_order": extract_regions_with_reading_order,
        "no_reading_order": extract_regions_without_reading_order
    }
    if reading_order not in strategies.keys():
        LOG.error("Unknown reading order extraction strategy %s, using default strategy.",
                  reading_order)
        reading_order = "reading_order"

    return strategies[reading_order]


def extract_regions_with_reading_order(tree, nsmap, **kwargs):
    """
    Extract regions in the order given by ReadingOrder element in the xml structure.

    Falls back to `extract_regions_without_reading_order` in case of missing data.
    """
    region_ids = []
    reading_order = tree.find('.//page:ReadingOrder', namespaces=nsmap)
    if reading_order is None:
        LOG.warning("No reading order, extract without.")
        return extract_regions_without_reading_order(tree, nsmap)

    for group in reading_order.iterfind('./*', namespaces=nsmap):
        if ET.QName(group.tag).localname != 'OrderedGroup':
            raise NotImplementedError

        region_ref_indexeds = group.findall('./page:RegionRefIndexed', namespaces=nsmap)
        region_ref_indexeds = sorted(region_ref_indexeds,
                                     key=lambda r: int(r.attrib['index']))
        region_ids = [region_ref_indexed.attrib['regionRef']
                      for region_ref_indexed in region_ref_indexeds]
    return region_ids


def extract_regions_without_reading_order(tree, nsmap, **kwargs):
    """
    Extract regions in the order they occur in the xml structure.

    This may result in unexpected results because the order is not guaranteed.
    """
    region_ids = [r.attrib['id'] for r in
                  tree.iterfind('.//page:TextRegion', namespaces=nsmap)]
    return region_ids


def extract_regions_grid(tree, nsmap, grid_direction="row", grid_size=10, **kwargs):
    """
    Recalculate the reading order on a grid.

    Maps the top left corner of a region polygon to a grid position.
    Multiple regions in the same grid position are ordered by their
    occurence in the xml structure.
    """
    img_dim = extract_img_dim(tree, nsmap)
    coords = extract_coords(tree, nsmap)
    grid_order = defaultdict(list)
    for region_id in sorted(coords.keys()):
        top_left = extract_top_left(coords[region_id])
        grid_id = map_point_to_grid(img_dim, top_left,
                                    grid_direction=grid_direction, grid_size=grid_size)
        grid_order[grid_id].append(region_id)
    sorted_ids = list(it.chain.from_iterable(
        grid_order[grid_id] for grid_id in sorted(grid_order.keys())))
    return sorted_ids


def extract_coords(tree, nsmap) -> Dict[str, str]:
    """Extract points from a Coords xml element (unstructured)."""
    regions = tree.findall('.//page:TextRegion', namespaces=nsmap)
    return {r.attrib['id']: r.find('page:Coords', namespaces=nsmap).attrib['points']
            for r in regions}


def extract_img_dim(tree, nsmap) -> Dimension:
    """Extract image dimensions from xml structure."""
    page = tree.find('page:Page', namespaces=nsmap)
    return Dimension(width=int(page.attrib["imageWidth"]),
                     height=int(page.attrib['imageHeight']))


def extract_top_left(coords: str) -> Point:
    """Extract the top left coordinates of a region polygon."""
    points = coords.split(' ')
    points = [point.split(",") for point in points]
    points = [(int(x), int(y)) for x, y in points]
    x, y = zip(*points)
    return Point(x=min(x), y=min(y))


def map_point_to_grid(img_dim: Dimension, point: Point, grid_direction="row",
                      grid_size: int = 10) -> int:
    """Map a point to a grid position on the image."""
    if point.x < 0 or point.y < 0:
        LOG.error("Negative coordinates not expected, set to 0.")
    if point.x > img_dim.width or point.y > img_dim.height:
        LOG.error("Point coordinates bigger than image, set to image size.")
    if grid_direction not in ("row", "col"):
        raise ValueError("Only 'row' or 'col' supported for grid reading direction.")

    x, y = min(max(0, point.x), img_dim.width), min(max(0, point.y), img_dim.height)

    grid_id = 1
    if grid_direction == "row":
        grid_id = math.ceil(img_dim.width / grid_size) \
                  * max(0, (math.ceil(y / grid_size) - 1)) \
                  + math.ceil(x / grid_size)
    elif grid_direction == "col":
        grid_id = math.ceil(img_dim.height / grid_size) \
                  * max(0, (math.ceil(x / grid_size) - 1)) \
                  + math.ceil(y / grid_size)

    return max(1, grid_id)
