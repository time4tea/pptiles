import pathlib
from io import BytesIO
from pathlib import Path

import bottle
from mapbox_vector_tile.decoder import TileData
from sqlitedict import SqliteDict

from maps import RequestsSource, PMReader, XYZ, FileSource
from parser import Parser
from test import draw

app = bottle.default_app()

cache = SqliteDict(filename="pmtile.sqlite", autocommit=True)

source = RequestsSource(
    uri="https://r2-public.protomaps.com/protomaps-sample-datasets/protomaps-basemap-opensource-20230408.pmtiles",
    cache=cache)

filesource = FileSource(Path("map.pmtiles"))
reader = PMReader(filesource)

p = pathlib.Path("style2.json")
style = Parser().parse(p)


@app.route("/<z:int>/<x:int>/<y:int>.png")
def tile(z, x, y):
    xyz = XYZ(x, y, z)
    surface = draw(style, xyz.z, TileData(reader.xyz(xyz)).get_message(), 512)
    out = BytesIO()
    surface.write_to_png(out)
    return bottle.HTTPResponse(out.getvalue(), content_type="image/png")


if __name__ == "__main__":
    bottle.run(host='0.0.0.0', port=8000)
