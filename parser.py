import json
import pathlib
from typing import Any, List, Optional

from colour import Colour
from drawing import LayerDrawingRule, PolygonFeatureDrawing, fill, drawcolour, ContextModification, multiple, f_all, f_false, FeatureFilter, f_true, f_property, f_has


class Parser:

    def parse(self, p: pathlib.Path):
        j = json.load(p.open())

        rules = []

        for layer in j["layers"]:
            layer_type_ = layer["type"]

            if layer_type_ == "background":
                continue

            layer_id_ = layer["id"]
            layer_source_ = layer["source-layer"]

            f_filter = self.parse_filter(layer.get("filter"))
            paint = self.parse_paint(layer.get("paint"))

            if layer_type_ == "fill":
                rules.append(
                    LayerDrawingRule(
                        layer_source_,
                        PolygonFeatureDrawing(fill(paint)),
                        f_filter
                    )
                )
            elif layer_type_ == "line":
                pass
            else:
                print(f"Unsupported layer type {layer_type_}")

    def parse_predicate(self, *terms) -> FeatureFilter:
        op = terms[0]
        prop: str = terms[1]
        rest = terms[2:]

        if prop.startswith("$"):
            print(f"Unsupported prop {prop}")
            return f_true()

        if op in {"==", "in"}:
            return f_property(prop, set(rest))
        elif op in {"has"}:
            return f_has(prop)
        else:
            print(f"Unsupported op {op}")
            return f_true()

    def parse_filter(self, filters: Optional[List[Any]]):
        if filters is None:
            return lambda x: True

        op = filters[0]

        if op == "all":
            predicates = [self.parse_predicate(*p) for p in filters[1:]]
            return f_all(*predicates)
        else:
            print(f"Unsupported op {op}")
            return f_false()

    def parse_paint(self, param) -> ContextModification:
        mods = []
        colour = param.get("fill-color")
        if colour is not None:
            mods.append(drawcolour(Colour.from_spec(colour)))
        return multiple(*mods)


if __name__ == "__main__":
    p = pathlib.Path("style.json")

    style = Parser().parse(p)
