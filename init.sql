CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS province (
 name text PRIMARY KEY,
 geom geometry(MultiPolygon,4326) NOT NULL,
 result jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS province_geom ON province USING gist(geom);
