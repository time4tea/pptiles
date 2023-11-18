
MAP_REGION=europe
MAP_NAME=britain-and-ireland-latest

MAP_FILE=$(MAP_NAME).osm.pbf
MAP_URL=https://download.geofabrik.de/$(MAP_REGION)/$(MAP_FILE)

CURL=curl --fail --silent

TILEMAKER=downloads/build/tilemaker

.PHONY: map
map: downloads/$(MAP_NAME).pmtiles

downloads:
	mkdir -p $@

downloads/$(MAP_FILE):
	$(CURL) -o $@ $(MAP_URL)

%.mbtiles: %.osm.pbf
	$(TILEMAKER) --input $< --output $@ --process downloads/resources/process-openmaptiles.lua --config downloads/resources/config-openmaptiles.json

%.pmtiles: %.mbtiles
	./pmtiles convert $< $@
