from __future__ import annotations

import dataclasses
from typing import Set, Callable

import cairo

from colour import Colour

ContextModification = Callable[[int, cairo.Context], None]


def multiple(*ms: ContextModification) -> ContextModification:
    def f(z: int, ctx: cairo.Context):
        [m(z, ctx) for m in ms]

    return f


def drawcolour(c: Colour) -> ContextModification:
    return lambda z, ctx: c.apply_to(ctx)


def linewidth(w: float) -> ContextModification:
    return lambda z, ctx: ctx.set_line_width(w)


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

        self.drawing(zoom, ctx)


FeatureFilter = Callable[[dict], bool]


def f_any() -> FeatureFilter:
    return lambda f: True


def f_property(name: str, wanted: Set[str]) -> FeatureFilter:
    return lambda f: f.get("properties", {}).get(name, None) in wanted


@dataclasses.dataclass(frozen=True)
class LayerDrawingRule:
    layer: str
    drawing: FeatureDrawing
    filter: FeatureFilter

    def draw(self, ctx: cairo.Context, zoom: int, tile: dict):
        if self.layer in tile:
            for feature in tile[self.layer]["features"]:
                if self.filter(feature):
                    self.drawing.draw(ctx, zoom, feature)
