FROM osrm/osrm-backend:v5.22.0

ENV continent=south-america
ENV country=colombia
ENV city=colombia

ARG bounding_box=-76.769106,3.139265,-72.394630,11.410498
ARG source=http://download.geofabrik.de/${continent}/${country}-latest.osm.pbf

RUN apt --yes update
RUN apt --yes install wget
RUN apt install --yes osmium-tool
RUN wget ${source} -O source.pbf
RUN osmium extract --bbox ${bounding_box}  source.pbf -o ${city}.pbf
RUN /usr/local/bin/osrm-extract -p /opt/car.lua ${city}.pbf
RUN /usr/local/bin/osrm-contract ${city}.osrm

ENTRYPOINT osrm-routed --algorithm ch ${city}.osrm