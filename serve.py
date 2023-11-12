from io import BytesIO
from pathlib import Path

import bottle
from mapbox_vector_tile.decoder import TileData
from sqlitedict import SqliteDict

from maps import RequestsSource, PMReader, XYZ, FileSource
from styles import rules
from test import draw

app = bottle.default_app()

cache = SqliteDict(filename="pmtile.sqlite", autocommit=True)

source = RequestsSource(
    uri="https://r2-public.protomaps.com/protomaps-sample-datasets/protomaps-basemap-opensource-20230408.pmtiles",
    cache=cache)

filesource = FileSource(Path("map.pmtiles"))
reader = PMReader(filesource)


@app.route("/<z:int>/<x:int>/<y:int>.png")
def tile(z, x, y):
    xyz = XYZ(x, y, z)
    surface = draw(rules, xyz.z, TileData(reader.xyz(xyz)).get_message())
    out = BytesIO()
    surface.write_to_png(out)
    return bottle.HTTPResponse(out.getvalue(), content_type="image/png")


bottle.run(host='127.0.0.1', port=8000)
