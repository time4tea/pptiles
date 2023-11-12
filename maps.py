import dataclasses
import gzip
import json
from collections import defaultdict
from functools import cached_property

import requests
from geotiler import Map
from geotiler.geo import WebMercator
from geotiler.map import _find_top_left_tile, _tile_coords, _tile_offsets
from geotiler.provider import MapProvider
from pmtiles.tile import deserialize_directory, deserialize_header, Compression, zxy_to_tileid, find_tile


class NullMapProvider(MapProvider):

    # noinspection PyMissingConstructor
    def __init__(self):
        self.projection = WebMercator(0)
        self.tile_width = 512
        self.tile_height = 512

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
    xyz: XYZ
    offset: Offset


class PMMap(Map):

    def __init__(self, extent=None, center=None, zoom=None, size=None) -> None:
        super().__init__(extent, center, zoom, size, NullMapProvider())

    def tiles(self):
        coord, offset = _find_top_left_tile(self)
        coords = [XYZ(c[0], c[1], self.zoom) for c in _tile_coords(self, coord, offset)]
        offsets = [Offset(o[0], o[1]) for o in _tile_offsets(self, offset)]

        return [Tile(xyz=z[0], offset=z[1]) for z in zip(coords, offsets)]


class Source:
    def load(self, offset: int, length: int):
        raise NotImplementedError()


class RequestsSource(Source):

    def __init__(self, uri, cache: dict):
        self.uri = uri
        self.cache = cache

    def load(self, offset, length):
        headers = {"Range": f"bytes={offset}-{offset + length - 1}"}

        key = f"{self.uri}{offset}{length}"
        if key not in self.cache:
            response = requests.get(url=self.uri, headers=headers)
            response.raise_for_status()
            self.cache[key] = response.content

        return self.cache[key]


class keydefaultdict(defaultdict):
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        else:
            ret = self[key] = self.default_factory(key)
            return ret


class PMReader:

    def __init__(self, source: Source):
        self.source = source
        self.directories = keydefaultdict(lambda ol: deserialize_directory(self.source.load(ol[0], ol[1])))

    def xyz(self, xyz: XYZ):
        return self.get(xyz.z, xyz.x, xyz.y)

    @cached_property
    def header(self):
        return deserialize_header(self.source.load(0, 127))

    @cached_property
    def metadata(self):
        header = self.header
        metadata = self.source.load(header["metadata_offset"], header["metadata_length"])
        if header["internal_compression"] == Compression.GZIP:
            metadata = gzip.decompress(metadata)
        return json.loads(metadata)

    @cached_property
    def _root_offset(self):
        return self.header["root_offset"]

    @cached_property
    def _root_length(self):
        return self.header["root_length"]

    @cached_property
    def _leaf_directory_offset(self):
        return self.header["leaf_directory_offset"]

    @cached_property
    def _tile_data_offset(self):
        return self.header["tile_data_offset"]

    @cached_property
    def _tile_compression(self) -> Compression:
        return self.header["tile_compression"]

    def _decompress_tile(self, d: bytes) -> bytes:
        if self._tile_compression == Compression.NONE:
            return d
        elif self._tile_compression == Compression.GZIP:
            return gzip.decompress(d)

    def get(self, z, x, y):
        tile_id = zxy_to_tileid(z, x, y)
        dir_offset = self._root_offset
        dir_length = self._root_length
        for depth in range(0, 4):  # max depth
            directory = self.directories[(dir_offset, dir_length)]
            result = find_tile(directory, tile_id)
            if result:
                if result.run_length == 0:
                    dir_offset = self._leaf_directory_offset + result.offset
                    dir_length = result.length
                else:
                    return self._decompress_tile(
                        self.source.load(self._tile_data_offset + result.offset, result.length)
                    )
