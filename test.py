import dataclasses

import requests
from geotiler import Map
from geotiler.geo import WebMercator
from geotiler.map import _find_top_left_tile, _tile_coords, _tile_offsets
from geotiler.provider import MapProvider
from pmtiles.reader import Reader
from sqlitedict import SqliteDict


class NullMapProvider(MapProvider):

    # noinspection PyMissingConstructor
    def __init__(self):
        self.projection = WebMercator(0)
        self.tile_width = 256
        self.tile_height = 256

    def tile_url(self, tile_coord, zoom):
        raise NotImplementedError()


@dataclasses.dataclass(frozen=True)
class XYZ:
    x: int
    y: int
    z: int


@dataclasses.dataclass(frozen=True)
class Offset:
    x: int
    y: int


@dataclasses.dataclass(frozen=True)
class Tile:
    locator: XYZ
    offset: Offset


class PMMap(Map):

    def __init__(self, extent=None, center=None, zoom=None, size=None) -> None:
        super().__init__(extent, center, zoom, size, NullMapProvider())

    def tiles(self):
        coord, offset = _find_top_left_tile(self)
        coords = [XYZ(c[0], c[1], map.zoom) for c in _tile_coords(self, coord, offset)]
        offsets = [Offset(o[0], o[1]) for o in _tile_offsets(self, offset)]

        return [Tile(locator=z[0], offset=z[1]) for z in zip(coords, offsets)]


class RequestsSource:

    def __init__(self, uri, cache: dict):
        self.uri = uri
        self.cache = cache

    def get_bytes(self, offset, length):
        print(f"Offset {offset}   Length {length} -> {offset + length - 1}")
        headers = {"Range": f"bytes={offset}-{offset + length - 1}"}

        key = f"{self.uri}{offset}{length}"
        if key not in self.cache:
            response = requests.get(url=self.uri, headers=headers)
            response.raise_for_status()
            self.cache[key] = response.content

        return self.cache[key]


class PMReader(Reader):

    def __init__(self, get_bytes):
        super().__init__(get_bytes)

    def xyz(self, xyz: XYZ):
        return super().get(xyz.z, xyz.x, xyz.y)


if __name__ == "__main__":
    map = PMMap(center=(51.445114, -0.264333), zoom=12, size=(500, 500))

    print(map.tiles())

    with SqliteDict(filename="pmtile.sqlite", autocommit=True) as cache:
        source = RequestsSource(
            uri="https://r2-public.protomaps.com/protomaps-sample-datasets/protomaps-basemap-opensource-20230408.pmtiles",
            cache=cache
        )

        reader = PMReader(source.get_bytes)

        for tile in map.tiles():
            reader.xyz(tile.locator)
