import colorsys
import dataclasses
import gzip
import json
from collections import defaultdict
from functools import cached_property
from typing import Tuple, Set, List

import cairo
import requests
from PIL import Image
from geotiler import Map
from geotiler.geo import WebMercator
from geotiler.map import _find_top_left_tile, _tile_coords, _tile_offsets
from geotiler.provider import MapProvider
from mapbox_vector_tile.decoder import TileData
from pmtiles.tile import deserialize_header, Compression, zxy_to_tileid, deserialize_directory, find_tile
from sqlitedict import SqliteDict


@dataclasses.dataclass(frozen=True)
class HLSColour:
    h: float
    l: float
    s: float
    a: float

    def lighten(self, by: float) -> 'HLSColour':
        return HLSColour(self.h, min(self.l + by, 1.0), self.s, self.a)

    def darken(self, by: float) -> 'HLSColour':
        return HLSColour(self.h, max(self.l - by, 0.0), self.s, self.a)

    def rgb(self) -> 'Colour':
        r, g, b = colorsys.hls_to_rgb(self.h, self.l, self.s)
        return Colour(r, g, b, self.a)

    def apply_to(self, context: cairo.Context):
        self.rgb().apply_to(context)


def hsl(h, s, l, a=1.0) -> HLSColour:
    return HLSColour(h, l, s, a)


@dataclasses.dataclass(frozen=True)
class Colour:
    r: float
    g: float
    b: float
    a: float = 1.0

    def rgba(self) -> Tuple[float, float, float, float]:
        return self.r, self.g, self.b, self.a

    def rgb(self) -> Tuple[float, float, float]:
        return self.r, self.g, self.b

    def hls(self) -> HLSColour:
        h, l, s = colorsys.rgb_to_hls(self.r, self.g, self.b)
        return HLSColour(h, l, s, self.a)

    def darken(self, by: float) -> 'Colour':
        return self.hls().darken(by).rgb()

    def lighten(self, by: float) -> 'Colour':
        return self.hls().lighten(by).rgb()

    def alpha(self, new_alpha: float):
        return Colour(self.r, self.g, self.b, new_alpha)

    @staticmethod
    def _rescale(t):
        return map(lambda v: v / 255.0, t)

    @staticmethod
    def hex(hexcolour: str, alpha=1.0):
        if hexcolour.startswith("#"):
            hexcolour = hexcolour[1:]
        r, g, b = Colour._rescale(tuple(int(hexcolour[i:i + 2], 16) for i in (0, 2, 4)))
        return Colour(r, g, b, alpha)

    @staticmethod
    def from_pil(r, g, b, a=255):
        return Colour(*Colour._rescale((r, g, b, a)))

    def apply_to(self, context: cairo.Context):
        context.set_source_rgba(*self.rgba())


class NullMapProvider(MapProvider):

    # noinspection PyMissingConstructor
    def __init__(self):
        self.projection = WebMercator(0)
        self.tile_width = 512
        self.tile_height = 512

    def tile_url(self, tile_coord, zoom):
        raise NotImplementedError()


@dataclasses.dataclass(frozen=True)
class XYZ:
    x: int
    y: int
    z: int


@dataclasses.dataclass(frozen=True)
class Offset:
    x: int
    y: int


@dataclasses.dataclass(frozen=True)
class Tile:
    locator: XYZ
    offset: Offset


class PMMap(Map):

    def __init__(self, extent=None, center=None, zoom=None, size=None) -> None:
        super().__init__(extent, center, zoom, size, NullMapProvider())

    def tiles(self):
        coord, offset = _find_top_left_tile(self)
        coords = [XYZ(c[0], c[1], self.zoom) for c in _tile_coords(self, coord, offset)]
        offsets = [Offset(o[0], o[1]) for o in _tile_offsets(self, offset)]

        return [Tile(locator=z[0], offset=z[1]) for z in zip(coords, offsets)]


class RequestsSource:

    def __init__(self, uri, cache: dict):
        self.uri = uri
        self.cache = cache

    def get_bytes(self, offset, length):
        headers = {"Range": f"bytes={offset}-{offset + length - 1}"}

        key = f"{self.uri}{offset}{length}"
        if key not in self.cache:
            response = requests.get(url=self.uri, headers=headers)
            response.raise_for_status()
            self.cache[key] = response.content

        return self.cache[key]


class keydefaultdict(defaultdict):
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        else:
            ret = self[key] = self.default_factory(key)
            return ret


class PMReader:

    def __init__(self, get_bytes):
        self.get_bytes = get_bytes
        self.directories = keydefaultdict(lambda ol: deserialize_directory(self.get_bytes(ol[0], ol[1])))

    def xyz(self, xyz: XYZ):
        return self.get(xyz.z, xyz.x, xyz.y)

    @cached_property
    def header(self):
        return deserialize_header(self.get_bytes(0, 127))

    @cached_property
    def metadata(self):
        header = self.header
        metadata = self.get_bytes(header["metadata_offset"], header["metadata_length"])
        if header["internal_compression"] == Compression.GZIP:
            metadata = gzip.decompress(metadata)
        return json.loads(metadata)

    @cached_property
    def _root_offset(self):
        return self.header["root_offset"]

    @cached_property
    def _root_length(self):
        return self.header["root_length"]

    @cached_property
    def _leaf_directory_offset(self):
        return self.header["leaf_directory_offset"]

    @cached_property
    def _tile_data_offset(self):
        return self.header["tile_data_offset"]

    @cached_property
    def _tile_compression(self) -> Compression:
        return self.header["tile_compression"]

    def _decompress_tile(self, d: bytes) -> bytes:
        if self._tile_compression == Compression.NONE:
            return d
        elif self._tile_compression == Compression.GZIP:
            return gzip.decompress(d)

    def get(self, z, x, y):
        tile_id = zxy_to_tileid(z, x, y)
        dir_offset = self._root_offset
        dir_length = self._root_length
        for depth in range(0, 4):  # max depth
            directory = self.directories[(dir_offset, dir_length)]
            result = find_tile(directory, tile_id)
            if result:
                if result.run_length == 0:
                    dir_offset = self._leaf_directory_offset + result.offset
                    dir_length = result.length
                else:
                    return self._decompress_tile(
                        self.get_bytes(self._tile_data_offset + result.offset, result.length)
                    )


class FeatureDrawing:
    def draw(self, ctx: cairo.Context, feature):
        raise NotImplementedError()


class PolygonFeatureDrawing(FeatureDrawing):
    def __init__(self, colour: Colour):
        self.colour = colour

    def draw(self, ctx: cairo.Context, feature):

        self.colour.apply_to(ctx)

        geometry = feature["geometry"]
        if geometry["type"] != "Polygon":
            print(f"unsupported feature type {geometry['type']}")
        else:
            for poly in geometry["coordinates"]:
                for i, xy in enumerate(poly):
                    if i == 0:
                        ctx.move_to(xy[0], 4096 - xy[1])
                    else:
                        ctx.line_to(xy[0], 4096 - xy[1])
                ctx.fill()


class LineFeatureDrawing(FeatureDrawing):
    def __init__(self, colour: Colour, width):
        self.colour = colour
        self.width = width

    def draw(self, ctx: cairo.Context, feature):
        self.colour.apply_to(ctx)

        ctx.set_line_width(self.width)

        geometry = feature["geometry"]
        geometry_type_ = geometry["type"]

        if geometry_type_ == "LineString":
            lines = [geometry["coordinates"]]
        elif geometry_type_ == "MultiLineString":
            lines = geometry["coordinates"]
        else:
            print(f"unsupported feature type {geometry_type_}")
            return

        for line in lines:
            for i, xy in enumerate(line):
                if i == 0:
                    ctx.move_to(xy[0], 4096 - xy[1])
                else:
                    ctx.line_to(xy[0], 4096 - xy[1])
            ctx.stroke()


style = {
    "earth": hsl(47 / 256, .26, .86),
    "glacier": hsl(47 / 256, .22, .94),
    "residential": hsl(.47, .13, .86),
    "hospital": Colour.hex("#B284BC"),
    "cemetery": Colour.hex("#333333"),
    "school": Colour.hex("#BBB993"),
    "industrial": Colour.hex("#FFF9EF"),
    "wood": hsl(82 / 256, .46, .72),
    "grass": hsl(82 / 256, .46, .72),
    "park": Colour.hex("#E5F9D5"),
    "water": hsl(205 / 256, .56, .73),
    "sand": hsl(232 / 256, 214 / 256, 38 / 256),
    "buildings": Colour.hex("#F2EDE8"),
    "highwayOuter": Colour.hex("#FFC3C3"),
    "majorRoadOuter": Colour.hex("#1C7C08"),
    "mediumRoadOuter": Colour.hex("#08547D"),
    "minorRoadOuter": Colour.hex("#2B087D"),
    "highway": Colour.hex("#FFCEBB"),
    "majorRoad": Colour.hex("#FFE4B3"),
    "mediumRoad": Colour.hex("#FFF2C8"),
    "minorRoad": Colour.hex("#ffffff"),
    "waterway": Colour.hex("94C1E1")
}


class FeatureFilter:
    def wants(self, feature) -> bool:
        raise NotImplementedError()


class AnyFeature(FeatureFilter):

    def wants(self, feature) -> bool:
        return True


class PropertyFilter(FeatureFilter):

    def __init__(self, name: str, wanted: Set[str]):
        self.name = name
        self.wanted = wanted

    def wants(self, feature) -> bool:
        return feature.get("properties", {}).get(self.name, None) in self.wanted


@dataclasses.dataclass(frozen=True)
class LayerDrawingRule:
    layer: str
    drawing: FeatureDrawing
    filter: FeatureFilter

    def draw(self, ctx: cairo.Context, tile: dict):
        if self.layer in tile:
            for feature in tile[self.layer]["features"]:
                if self.filter.wants(feature):
                    self.drawing.draw(ctx, feature)


rules = [
    LayerDrawingRule(
        "earth",
        PolygonFeatureDrawing(style["earth"]),
        AnyFeature()
    ),
    LayerDrawingRule(
        "natural",
        PolygonFeatureDrawing(style["wood"]),
        PropertyFilter("natural", {"wood"})
    ),
    LayerDrawingRule(
        "natural",
        PolygonFeatureDrawing(style["sand"]),
        PropertyFilter("natural", {"sand"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(style["residential"]),
        PropertyFilter("landuse", {"residential", "neighbourhood"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(style["hospital"]),
        PropertyFilter("amenity", {"hospital"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(style["school"]),
        PropertyFilter("amenity", {"school", "kindergarten", "university", "college"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(style["industrial"]),
        PropertyFilter("landuse", {"industrial"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(style["grass"]),
        PropertyFilter("landuse", {"grass"})
    ),
    LayerDrawingRule(
        "buildings",
        PolygonFeatureDrawing(style["buildings"]),
        AnyFeature()
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(style["park"]),
        PropertyFilter("landuse", {"park"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(style["highwayOuter"], 5),
        PropertyFilter("pmap:kind", {"highway"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(style["highway"], 4),
        PropertyFilter("pmap:kind", {"highway"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(style["majorRoadOuter"], 4),
        PropertyFilter("pmap:kind", {"major_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(style["majorRoad"], 3),
        PropertyFilter("pmap:kind", {"major_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(style["mediumRoadOuter"], 3),
        PropertyFilter("pmap:kind", {"medium_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(style["mediumRoad"], 2),
        PropertyFilter("pmap:kind", {"medium_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(style["minorRoadOuter"], 2),
        PropertyFilter("pmap:kind", {"minor_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(style["minorRoad"], 1),
        PropertyFilter("pmap:kind", {"minor_road"})
    ),
    LayerDrawingRule(
        "water",
        PolygonFeatureDrawing(style["waterway"]),
        AnyFeature()
    )
]


def draw(rules: List[LayerDrawingRule], tile: dict) -> cairo.ImageSurface:
    size = 512

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    ctx.scale(size / 4096, size / 4096)

    ctx.set_line_width(2)

    for rule in rules:
        rule.draw(ctx, tile)

    return surface


def to_pillow(surface: cairo.ImageSurface) -> Image:
    size = (surface.get_width(), surface.get_height())
    stride = surface.get_stride()

    format = surface.get_format()
    if format != cairo.FORMAT_ARGB32:
        raise IOError(f"Only support ARGB32 images, not {format}")

    with surface.get_data() as memory:
        return Image.frombuffer("RGBA", size, memory.tobytes(), 'raw', "BGRa", stride)


if __name__ == "__main__":
    pmmap = PMMap(center=(-0.264333, 51.445114), zoom=13, size=(500, 500))

    with SqliteDict(filename="pmtile.sqlite", autocommit=True) as cache:
        source = RequestsSource(
            uri="https://r2-public.protomaps.com/protomaps-sample-datasets/protomaps-basemap-opensource-20230408.pmtiles",
            cache=cache
        )

        reader = PMReader(source.get_bytes)

        for tile in pmmap.tiles():
            message = TileData(reader.xyz(tile.locator)).get_message()

            to_pillow(draw(rules, message)).show()
