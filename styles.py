from colour import hsl, Colour
from drawing import LayerDrawingRule, PolygonFeatureDrawing, LineFeatureDrawing, drawcolour, multiple, f_any, \
    f_property, fill, stroke, linewidthexp, stroke_preserve, fill_preserve, linewidth

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
    "highway": Colour.hex("#FFCEBB"),
    "majorRoadOuter": Colour.hex("#1C7C08"),
    "majorRoad": Colour.hex("#FFE4B3"),
    "mediumRoadOuter": Colour.hex("#08547D"),
    "mediumRoad": Colour.hex("#FFF2C8"),
    "minorRoadOuter": Colour.hex("#2B087D"),
    "minorRoad": Colour.hex("#ffffff"),
    "waterway": Colour.hex("94C1E1")
}
rules = [
    LayerDrawingRule(
        "earth",
        PolygonFeatureDrawing(fill(drawcolour(style["earth"]))),
        f_any()
    ),
    LayerDrawingRule(
        "natural",
        PolygonFeatureDrawing(fill(drawcolour(style["wood"]))),
        f_property("natural", {"wood"})
    ),
    LayerDrawingRule(
        "natural",
        PolygonFeatureDrawing(fill(drawcolour(style["sand"]))),
        f_property("natural", {"sand"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(fill(drawcolour(style["residential"]))),
        f_property("landuse", {"residential", "neighbourhood"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(fill(drawcolour(style["hospital"]))),
        f_property("amenity", {"hospital"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(fill(drawcolour(style["school"]))),
        f_property("amenity", {"school", "kindergarten", "university", "college"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(fill(drawcolour(style["industrial"]))),
        f_property("landuse", {"industrial"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(
            multiple(
                fill_preserve(drawcolour(style["grass"])),
                stroke(drawcolour(Colour.hex("00ff00"))),
            )
        ),
        f_property("landuse", {"grass"})
    ),
    LayerDrawingRule(
        "buildings",
        PolygonFeatureDrawing(
            multiple(
                fill_preserve(drawcolour(style["buildings"])),
                stroke(drawcolour(Colour.hex("ff0000"))),
            )
        ),
        f_any()
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(fill(drawcolour(style["park"]))),
        f_property("landuse", {"park"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(stroke(multiple(drawcolour(style["highwayOuter"]), linewidth(5)))),
        f_property("pmap:kind", {"highway"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(stroke(multiple(drawcolour(style["highway"]), linewidth(4)))),
        f_property("pmap:kind", {"highway"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(
            multiple(
                stroke_preserve(multiple(drawcolour(style["majorRoadOuter"]), linewidthexp(1.4, [
                    (9, 3),
                    (12, 4),
                    (17, 8),
                    (20, 22),
                ]))),
                stroke(multiple(drawcolour(style["majorRoad"]), linewidthexp(1.4, [
                    (9, 2),
                    (12, 3),
                    (17, 6),
                    (20, 20),
                ])))
            )
        ),
        f_property("pmap:kind", {"major_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(stroke(multiple(drawcolour(style["majorRoad"]), linewidth(3)))),
        f_property("pmap:kind", {"major_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(stroke(multiple(drawcolour(style["mediumRoadOuter"]), linewidth(3)))),
        f_property("pmap:kind", {"medium_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(stroke(multiple(drawcolour(style["mediumRoad"]), linewidth(2)))),
        f_property("pmap:kind", {"medium_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(stroke(multiple(drawcolour(style["minorRoadOuter"]), linewidth(2)))),
        f_property("pmap:kind", {"minor_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(stroke(multiple(drawcolour(style["minorRoad"]), linewidth(1)))),
        f_property("pmap:kind", {"minor_road"})
    ),
    LayerDrawingRule(
        "water",
        PolygonFeatureDrawing(fill(drawcolour(style["waterway"]))),
        f_any()
    )
]
