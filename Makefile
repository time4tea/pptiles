

MBTILES=/home/richja/dev/tileserver/data/maptiler-osm-2017-07-03-v3.6.1-europe_great-britain.mbtiles


map.pmtiles: $(MBTILES)
	./pmtiles convert $< $@