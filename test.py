import contextlib

import pmtiles.reader
import requests
from sqlitedict import SqliteDict


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

if __name__ == "__main__":
    with SqliteDict(filename="pmtile.sqlite", autocommit=True) as cache:
        source = RequestsSource(
            uri="https://r2-public.protomaps.com/protomaps-sample-datasets/protomaps-basemap-opensource-20230408.pmtiles",
            cache=cache
        )

        reader = pmtiles.reader.Reader(source.get_bytes)

        reader.get(11, 1102, 1090)
