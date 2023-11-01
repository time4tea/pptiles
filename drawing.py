from __future__ import annotations

import dataclasses
from typing import Sequence, Set

import cairo

from colour import Colour


class ContextModification:
    def modify(self, ctx: cairo.Context):
        raise NotImplementedError()


class ContextModifications(ContextModification):
    def __init__(self, modifications: Sequence[ContextModification]):
        self.modifications = modifications

    def modify(self, ctx: cairo.Context):
        [m.modify(ctx) for m in self.modifications]


def multiple(*m: ContextModification) -> ContextModification:
    return ContextModifications(m)


class DrawColour(ContextModification):

    def __init__(self, colour: Colour):
        self.colour = colour

    def modify(self, ctx: cairo.Context):
        self.colour.apply_to(ctx)


def drawcolour(c: Colour) -> ContextModification:
    return DrawColour(c)


class LineWidth(ContextModification):

    def __init__(self, width):
        self.width = width

    def modify(self, ctx: cairo.Context):
        ctx.set_line_width(self.width)


def linewidth(w: float) -> ContextModification:
    return LineWidth(w)


class LineCap(ContextModification):

    def __init__(self, cap: cairo.LineCap):
        self.cap = cap

    def modify(self, ctx: cairo.Context):
        ctx.set_line_cap(self.cap)


class LineJoin(ContextModification):

    def __init__(self, join: cairo.LineJoin):
        self.join = join

    def modify(self, ctx: cairo.Context):
        ctx.set_line_join(self.join)


class LineDash(ContextModification):

    def __init__(self, dash: Sequence[float]):
        self.dash = dash

    def modify(self, ctx: cairo.Context):
        ctx.set_dash(self.dash)


def linedash(*w: float) -> ContextModification:
    return LineDash(w)


class FeatureDrawing:
    def draw(self, ctx: cairo.Context, feature):
        raise NotImplementedError()


class PolygonFeatureDrawing(FeatureDrawing):
    def __init__(self, modification: ContextModification):
        self.modification = modification

    def draw(self, ctx: cairo.Context, feature):

        self.modification.modify(ctx)

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
                ctx.fill()


class LineFeatureDrawing(FeatureDrawing):
    def __init__(self, modification: ContextModification):
        self.modification = modification

    def draw(self, ctx: cairo.Context, feature):

        self.modification.modify(ctx)

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
