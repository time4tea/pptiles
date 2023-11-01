from colour import hsl, Colour
from drawing import LayerDrawingRule, PolygonFeatureDrawing, AnyFeature, PropertyFilter, LineFeatureDrawing, drawcolour, multiple, linewidth

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
rules = [
    LayerDrawingRule(
        "earth",
        PolygonFeatureDrawing(drawcolour(style["earth"])),
        AnyFeature()
    ),
    LayerDrawingRule(
        "natural",
        PolygonFeatureDrawing(drawcolour(style["wood"])),
        PropertyFilter("natural", {"wood"})
    ),
    LayerDrawingRule(
        "natural",
        PolygonFeatureDrawing(drawcolour(style["sand"])),
        PropertyFilter("natural", {"sand"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(drawcolour(style["residential"])),
        PropertyFilter("landuse", {"residential", "neighbourhood"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(drawcolour(style["hospital"])),
        PropertyFilter("amenity", {"hospital"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(drawcolour(style["school"])),
        PropertyFilter("amenity", {"school", "kindergarten", "university", "college"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(drawcolour(style["industrial"])),
        PropertyFilter("landuse", {"industrial"})
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(drawcolour(style["grass"])),
        PropertyFilter("landuse", {"grass"})
    ),
    LayerDrawingRule(
        "buildings",
        PolygonFeatureDrawing(drawcolour(style["buildings"])),
        AnyFeature()
    ),
    LayerDrawingRule(
        "landuse",
        PolygonFeatureDrawing(drawcolour(style["park"])),
        PropertyFilter("landuse", {"park"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["highwayOuter"]), linewidth(5))),
        PropertyFilter("pmap:kind", {"highway"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["highway"]), linewidth(4))),
        PropertyFilter("pmap:kind", {"highway"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["majorRoadOuter"]), linewidth(4))),
        PropertyFilter("pmap:kind", {"major_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["majorRoad"]), linewidth(3))),
        PropertyFilter("pmap:kind", {"major_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["mediumRoadOuter"]), linewidth(3))),
        PropertyFilter("pmap:kind", {"medium_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["mediumRoad"]), linewidth(2))),
        PropertyFilter("pmap:kind", {"medium_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["minorRoadOuter"]), linewidth(2))),
        PropertyFilter("pmap:kind", {"minor_road"})
    ),
    LayerDrawingRule(
        "roads",
        LineFeatureDrawing(multiple(drawcolour(style["minorRoad"]), linewidth(1))),
        PropertyFilter("pmap:kind", {"minor_road"})
    ),
    LayerDrawingRule(
        "water",
        PolygonFeatureDrawing(drawcolour(style["waterway"])),
        AnyFeature()
    )
]
