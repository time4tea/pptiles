from typing import List

import cairo
from mapbox_vector_tile.decoder import TileData
from sqlitedict import SqliteDict

from colour import Colour
from drawing import PolygonFeatureDrawing, LineFeatureDrawing, LayerDrawingRule, multiple, \
    drawcolour, linewidth, linedash, fill, f_any, f_property, stroke
from image import to_pillow
from maps import PMMap, RequestsSource, PMReader
from styles import style, rules

test_rules = [
    LayerDrawingRule(
        "earth",
        PolygonFeatureDrawing(
            drawing=fill(multiple(drawcolour(style["earth"])), )
        ),
        f_any()
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(
            drawing=fill(drawcolour(style["residential"]))
        ),
        f_property("landuse", {"residential", "neighbourhood"})
    ),

    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(
            drawing=stroke(multiple(drawcolour(Colour.hex("ffffff")), linewidth(5), linedash(20, 10)))),
        f_property("pmap:kind", {"minor_road"})
    ),
]


def draw(rules: List[LayerDrawingRule], zoom: int, tile: dict) -> cairo.ImageSurface:
    size = 1024

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    ctx.scale(size / 4096, size / 4096)

    ctx.set_line_width(2)

    for rule in rules:
        rule.draw(ctx, zoom, tile)

    return surface


if __name__ == "__main__":
    pmmap = PMMap(center=(-0.264333, 51.445114), zoom=12, size=(500, 500))

    with SqliteDict(filename="pmtile.sqlite", autocommit=True) as cache:
        source = RequestsSource(
            uri="https://r2-public.protomaps.com/protomaps-sample-datasets/protomaps-basemap-opensource-20230408.pmtiles",
            cache=cache
        )

        reader = PMReader(source.get_bytes)

        for tile in pmmap.tiles()[0:1]:
            message = TileData(reader.xyz(tile.locator)).get_message()

            to_pillow(draw(rules, tile.locator.z, message)).show()
