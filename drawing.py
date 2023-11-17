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
    return lambda z: None


def multiple(*ms: ContextModification) -> ContextModification:
    def f(z: int, ctx: cairo.Context):
        [m(z, ctx) for m in ms]

    return f


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


def linecap(cap: cairo.LineCap) -> ContextModification:
    return lambda z, ctx: ctx.set_line_cap(cap)


def linejoin(join: cairo.LineJoin) -> ContextModification:
    return lambda z, ctx: ctx.set_line_join(join)


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


class PolygonFeatureDrawing(FeatureDrawing):
    def __init__(self, drawing: Drawing):
        self.drawing = drawing

    def draw(self, ctx: cairo.Context, zoom, feature):
        geometry = feature["geometry"]
        if geometry["type"] != "Polygon":
            pass
            # print(f"unsupported feature type {geometry['type']}")
        else:
            for poly in geometry["coordinates"]:
                for i, xy in enumerate(poly):
                    if i == 0:
                        ctx.move_to(xy[0], 4096 - xy[1])
                    else:
                        ctx.line_to(xy[0], 4096 - xy[1])
            with saved(ctx):
                self.drawing(zoom, ctx)


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
        else:
            print(f"unsupported feature type {geometry_type_}")
            return

        for line in lines:
            for i, xy in enumerate(line):
                if i == 0:
                    ctx.move_to(xy[0], 4096 - xy[1])
                else:
                    ctx.line_to(xy[0], 4096 - xy[1])

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
    def g(f):
        return f.get("geometry", {}).get(name, None) in wanted

    return lambda f: g(f)


def f_property(name: str, wanted: Set[str]) -> FeatureFilter:
    def p(f):
        return f.get("properties", {}).get(name, None) in wanted

    return lambda f: p(f)


def f_has(name: str) -> FeatureFilter:
    return lambda f: name in f.get("properties", {})


def f_not(predicate: FeatureFilter) -> FeatureFilter:
    return lambda f: not predicate(f)


ZoomFilter = Callable[[int], bool]


def above(i: int) -> ZoomFilter:
    return lambda z: z >= i


def below(i: int) -> ZoomFilter:
    return lambda z: z <= i


def between(i: int, j: int) -> ZoomFilter:
    return lambda z: i <= z <= j


class LayerDrawingRule:
    def draw(self, ctx: cairo.Context, zoom: int, tile: dict):
        raise NotImplementedError()


class BackgroundLayerDrawingRule(LayerDrawingRule):

    def __init__(self, drawing: Drawing):
        self.drawing = drawing

    def draw(self, ctx: cairo.Context, zoom: int, tile: dict):
        target:cairo.ImageSurface = ctx.get_target()
        nctx = cairo.Context(target)
        nctx.rectangle(0,0, target.get_width(), target.get_height())
        self.drawing(0, nctx)

@dataclasses.dataclass(frozen=True)
class FeatureLayerDrawingRule(LayerDrawingRule):
    layer: str
    drawing: FeatureDrawing
    filter: FeatureFilter
    zooms: ZoomFilter = lambda z: True

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
