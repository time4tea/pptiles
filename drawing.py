from __future__ import annotations

import bisect
import contextlib
import dataclasses
import math
from typing import Set, Callable, List, Tuple

import cairo

from colour import Colour

ContextModification = Callable[[int, cairo.Context], None]


def nothing() -> ContextModification:
    return lambda z, ctx: None


def multiple(*ms: ContextModification) -> ContextModification:
    def f(z: int, ctx: cairo.Context):
        [m(z, ctx) for m in ms]

    return f


def linecap(cap: cairo.LineCap) -> ContextModification:
    return lambda z, ctx: ctx.set_line_cap(cap)


def linejoin(join: cairo.LineJoin) -> ContextModification:
    return lambda z, ctx: ctx.set_line_join(join)


def drawcolour(c: Colour) -> ContextModification:
    return lambda z, ctx: c.apply_to(ctx)


def linewidth(w: float) -> ContextModification:
    return lambda z, ctx: ctx.set_line_width(w)


def widthexp(base: float, stops: List[Tuple[int, int]]) -> Callable[[int], float]:
    def fact(z, idx):
        d = stops[idx + 1][0] - stops[idx][0]
        p = z - stops[idx][0]

        if d == 0:
            return 0
        elif base == 1:
            return p / d
        else:
            return (math.pow(base, p) - 1) / (math.pow(base, d) - 1)

    def lerp(factor, start, end):
        return factor * (end - start) + start

    def f(z):
        if z < stops[0][0]:
            return stops[0][1]
        if z > stops[-1][0]:
            return stops[-1][1]
        i = bisect.bisect_left(stops, z, key=lambda s: s[0]) - 1
        factor = fact(z, i)
        w = lerp(factor, stops[i][1], stops[i + 1][1])
        return w * 5  # i don't know why this need multiplying. too small otherwise..

    return f


def linewidthexp(base: float, stops: List[Tuple[int, int]]) -> ContextModification:
    f = widthexp(base, stops)
    return lambda z, ctx: ctx.set_line_width(f(z))


def linedash(*w: float) -> ContextModification:
    return lambda z, ctx: ctx.set_dash(w)


Drawing = Callable[[int, cairo.Context], None]


def fill(m: ContextModification) -> Drawing:
    def f(z: int, ctx: cairo.Context):
        m(z, ctx)
        ctx.fill()

    return f


def fill_preserve(m: ContextModification) -> Drawing:
    def f(z: int, ctx: cairo.Context):
        m(z, ctx)
        ctx.fill_preserve()

    return f


def stroke(m: ContextModification) -> Drawing:
    def f(z: int, ctx: cairo.Context):
        m(z, ctx)
        ctx.stroke()

    return f


def stroke_preserve(m: ContextModification) -> Drawing:
    def f(z: int, ctx: cairo.Context):
        m(z, ctx)
        ctx.stroke_preserve()

    return f


class FeatureDrawing:
    def draw(self, ctx: cairo.Context, zoom: int, feature):
        raise NotImplementedError()


@contextlib.contextmanager
def saved(ctx: cairo.Context):
    try:
        ctx.save()
        yield
    finally:
        ctx.restore()


def do_primitive(ctx, lines_or_polys):
    for line in lines_or_polys:
        for i, xy in enumerate(line):
            if i == 0:
                ctx.move_to(xy[0], 4096 - xy[1])
            else:
                ctx.line_to(xy[0], 4096 - xy[1])


class PolygonFeatureDrawing(FeatureDrawing):
    def __init__(self, drawing: Drawing):
        self.drawing = drawing

    def draw(self, ctx: cairo.Context, zoom, feature):
        geometry = feature["geometry"]
        geometry_type_ = geometry["type"]

        if geometry_type_ == "Polygon":
            do_primitive(ctx, geometry["coordinates"])
        elif geometry_type_ == "MultiPolygon":
            [do_primitive(ctx, g) for g in geometry["coordinates"]]
        else:
            print(f"unsupported feature type {geometry['type']}")
            return

        with saved(ctx):
            self.drawing(zoom, ctx)


class TextFeatureDrawing(FeatureDrawing):
    def __init__(self,
                 font_name: str,
                 field_name: str,
                 text_anchor: str,
                 text_colour: Colour,
                 halo_colour: Colour,
                 halo_width: float,
                 ):
        self.font = cairo.ToyFontFace(font_name, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.field_name = field_name
        self.text_colour = text_colour
        self.halo_colour = halo_colour
        self.halo_size = halo_width
        self.text_anchor = text_anchor

    def draw(self, ctx: cairo.Context, zoom, feature):
        geometry = feature["geometry"]
        geometry_type_ = geometry["type"]

        if geometry_type_ != "Point":
            print(f"unsupported point feature geometry type {geometry_type_}")
            return

        coordinates = geometry["coordinates"]

        properties = feature["properties"]

        if self.field_name in properties:
            text = properties[self.field_name]
        else:
            parts = self.field_name.split("_")
            latin = f"{parts[0]}:latin"
            if latin in properties:
                text = properties[latin]
            else:
                print(f"Can't find {self.field_name} in {properties}")
                text = "?"

        with saved(ctx):
            ctx.set_font_face(self.font)
            ctx.set_font_size(150)

            extents = ctx.text_extents(text)
            if self.text_anchor == "center":
                ctx.translate(-extents.width / 2, extents.height / 2)

            if self.halo_size > 0:
                scaled = ctx.get_scaled_font()
                glyphs = scaled.text_to_glyphs(coordinates[0], coordinates[1], text)
                ctx.glyph_path(glyphs[0])

                ctx.set_line_width(self.halo_size * 10)
                ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                self.halo_colour.apply_to(ctx)
                ctx.stroke()

            ctx.move_to(coordinates[0], coordinates[1])
            self.text_colour.apply_to(ctx)
            ctx.show_text(text)


class CircleFeatureDrawing(FeatureDrawing):
    def __init__(self, drawing: Drawing):
        self.drawing = drawing

    def draw(self, ctx: cairo.Context, zoom, feature):
        geometry = feature["geometry"]
        geometry_type_ = geometry["type"]

        if geometry_type_ != "Point":
            print(f"unsupported point feature geometry type {geometry_type_}")
            return

        coordinates = geometry["coordinates"]

        with saved(ctx):
            Colour.hex("#ff0000").apply_to(ctx)
            ctx.new_sub_path()
            ctx.arc(coordinates[0], coordinates[1], 50, 0, math.tau)
            ctx.fill()


class LineFeatureDrawing(FeatureDrawing):
    def __init__(self, drawing: Drawing):
        self.drawing = drawing

    def draw(self, ctx: cairo.Context, zoom, feature):
        geometry = feature["geometry"]
        geometry_type_ = geometry["type"]

        if geometry_type_ == "LineString":
            lines = [geometry["coordinates"]]
        elif geometry_type_ == "MultiLineString":
            lines = geometry["coordinates"]
        elif geometry_type_ == "Polygon":
            lines = geometry["coordinates"]
        else:
            print(f"unsupported line feature geometry type {geometry_type_}")
            return

        do_primitive(ctx, lines)

        with saved(ctx):
            self.drawing(zoom, ctx)


FeatureFilter = Callable[[dict], bool]


def f_true() -> FeatureFilter:
    return lambda f: True


def f_false() -> FeatureFilter:
    return lambda f: False


def f_any(*predicates: FeatureFilter) -> FeatureFilter:
    return lambda f: any([p(f) for p in predicates])


def f_all(*predicates: FeatureFilter) -> FeatureFilter:
    return lambda f: all([p(f) for p in predicates])


def f_geometry(name: str, wanted: Set[str]) -> FeatureFilter:
    return lambda f: f.get("geometry", {}).get(name, None) in wanted


def f_property(name: str, wanted: Set[str]) -> FeatureFilter:
    return lambda f: f.get("properties", {}).get(name, None) in wanted


def f_has(name: str) -> FeatureFilter:
    return lambda f: name in f.get("properties", {})


def f_not(predicate: FeatureFilter) -> FeatureFilter:
    return lambda f: not predicate(f)


ZoomFilter = Callable[[int], bool]


def z_all() -> ZoomFilter:
    return lambda z: True


def z_above(i: int) -> ZoomFilter:
    return lambda z: z >= i


def z_below(i: int) -> ZoomFilter:
    return lambda z: z <= i


def z_between(i: int, j: int) -> ZoomFilter:
    return lambda z: i <= z <= j


class LayerDrawingRule:
    def draw(self, ctx: cairo.Context, zoom: int, tile: dict):
        raise NotImplementedError()


class BackgroundLayerDrawingRule(LayerDrawingRule):

    def __init__(self, id: str, drawing: Drawing):
        self.id = id
        self.drawing = drawing

    def draw(self, ctx: cairo.Context, zoom: int, tile: dict):
        target: cairo.ImageSurface = ctx.get_target()
        nctx = cairo.Context(target)
        nctx.rectangle(0, 0, target.get_width(), target.get_height())
        self.drawing(0, nctx)


@dataclasses.dataclass(frozen=True)
class FeatureLayerDrawingRule(LayerDrawingRule):
    layer: str
    drawing: FeatureDrawing
    filter: FeatureFilter
    id: str = "unspecified"
    zooms: ZoomFilter = z_all()

    def draw(self, ctx: cairo.Context, zoom: int, tile: dict):
        if self.zooms(zoom):
            if self.layer in tile:
                for feature in tile[self.layer]["features"]:
                    if self.filter(feature):
                        # print(f"Drawing {self.layer} -> {feature['properties']}")
                        self.drawing.draw(ctx, zoom, feature)


def draw(rules: List[LayerDrawingRule], zoom: int, tile: dict, size=256) -> cairo.ImageSurface:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    ctx.scale(size / 4096, size / 4096)

    ctx.set_line_width(2)

    for rule in rules:
        rule.draw(ctx, zoom, tile)

    return surface


if __name__ == "__main__":
    w = widthexp(1.4, [
        (13, 2),
        (17, 4),
        (20, 15),
    ])
    print(w(14))
