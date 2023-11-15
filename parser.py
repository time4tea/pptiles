import json
import pathlib
from typing import Any, List, Optional

from colour import Colour
from drawing import LayerDrawingRule, PolygonFeatureDrawing, fill, drawcolour, ContextModification, multiple, f_all, \
    f_false, FeatureFilter, f_true, f_property, f_has, f_not, LineFeatureDrawing, stroke, f_geometry, nothing, linewidthexp, widthexp


class Parser:

    def parse(self, p: pathlib.Path):
        j = json.load(p.open())

        rules = []

        for layer in j["layers"]:

            layer_type_ = layer["type"]

            if layer_type_ == "background":
                continue

            layer_source_ = layer["source"]

            if layer_source_ != "openmaptiles":
                continue

            layer_id_ = layer["id"]
            source_layer_ = layer["source-layer"]

            f_filter = self.parse_filter(layer.get("filter"))

            if layer_type_ == "fill":
                paint = self.parse_paint(layer.get("paint"))
                rules.append(
                    LayerDrawingRule(
                        source_layer_,
                        PolygonFeatureDrawing(fill(paint)),
                        f_filter
                    )
                )
            elif layer_type_ == "line":
                paint = self.parse_paint(layer.get("paint"))
                rules.append(
                    LayerDrawingRule(
                        source_layer_,
                        LineFeatureDrawing(stroke(paint)),
                        f_filter
                    )
                )
            else:
                print(f"Unsupported layer type {layer_type_}")
        return rules

    def parse_predicate(self, *terms) -> FeatureFilter:
        op = terms[0]
        prop: str = terms[1]
        rest = terms[2:]

        if prop.startswith("$"):
            gprop = prop.replace("$", "")
            if op in { "==", "in"}:
                return f_geometry(gprop, set(rest))
            else:
                print(f"Unsupported prop {prop} op {op}")
                return f_true()

        if op in {"==", "in"}:
            return f_property(prop, set(rest))
        elif op in {"has"}:
            return f_has(prop)
        elif op in {"!in", "!="}:
            return f_not(f_property(prop, set(rest)))
        else:
            print(f"Unsupported predicate op {op}")
            return f_true()

    def parse_filter(self, filters: Optional[List[Any]]):
        if filters is None:
            return lambda x: True

        op = filters[0]

        if op == "all":
            predicates = [self.parse_predicate(*p) for p in filters[1:]]
            return f_all(*predicates)
        elif op == "==":
            return self.parse_predicate(*filters)
        else:
            print(f"Unsupported op {op}")
            return f_false()

    def parse_line_width(self, rule: dict):
        if "base" in rule:
            return linewidthexp(
                rule["base"],
                rule["stops"]
            )
        else:
            return nothing()

    def parse_paint(self, param: dict) -> ContextModification:

        rules = {
            "fill-color": lambda v: drawcolour(Colour.from_spec(v)),
            "line-color": lambda v: drawcolour(Colour.from_spec(v)),
            "line-width": lambda v: self.parse_line_width(v),
        }

        mods = []

        for k, v in param.items():
            if k in rules:
                mods.append(rules[k](v))

        return multiple(*mods)


if __name__ == "__main__":
    # p = pathlib.Path("style2.json")
    # style = Parser().parse(p)
    # print(style)


    x = widthexp(1.2, [(5, 0.4), (6, 0.7), (7, 1.75), (20, 22)])
    print(x(13))