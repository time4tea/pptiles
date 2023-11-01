from typing import List

import cairo
from mapbox_vector_tile.decoder import TileData
from sqlitedict import SqliteDict

from colour import Colour
from drawing import PolygonFeatureDrawing, LineFeatureDrawing, AnyFeature, PropertyFilter, LayerDrawingRule, multiple, drawcolour, linewidth
from image import to_pillow
from maps import PMMap, RequestsSource, PMReader
from styles import style

test_rules = [
    LayerDrawingRule(
        "earth",
        PolygonFeatureDrawing(multiple(drawcolour(Colour.hex("000000")))),
        AnyFeature()
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["minorRoadOuter"]), linewidth(5))),
        PropertyFilter("pmap:kind", {"minor_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["minorRoad"]), linewidth(4))),
        PropertyFilter("pmap:kind", {"minor_road"})
    ),
]


def draw(rules: List[LayerDrawingRule], tile: dict) -> cairo.ImageSurface:
    size = 1024

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    ctx.scale(size / 4096, size / 4096)

    ctx.set_line_width(2)

    for rule in rules:
        rule.draw(ctx, tile)

    return surface


if __name__ == "__main__":
    pmmap = PMMap(center=(-0.264333, 51.445114), zoom=13, size=(500, 500))

    with SqliteDict(filename="pmtile.sqlite", autocommit=True) as cache:
        source = RequestsSource(
            uri="https://r2-public.protomaps.com/protomaps-sample-datasets/protomaps-basemap-opensource-20230408.pmtiles",
            cache=cache
        )

        reader = PMReader(source.get_bytes)

        for tile in pmmap.tiles()[0:1]:
            message = TileData(reader.xyz(tile.locator)).get_message()

            to_pillow(draw(test_rules, message)).show()
