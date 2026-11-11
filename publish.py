import json
import os
from pathlib import Path
import psycopg
def main():
    snapshot=json.loads(Path("web/src/snapshot.json").read_text(encoding="utf8"))
    with psycopg.connect(os.environ["DATABASE_URL"]) as db:
        db.execute(Path("sql/init.sql").read_text(encoding="utf8"))
        for f in snapshot["features"]:
            name=f["properties"]["name"]
            db.execute("""INSERT INTO province(name,geom,result) VALUES
                (%s,ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)),%s::jsonb)
                ON CONFLICT(name) DO UPDATE SET geom=excluded.geom,result=excluded.result""",
                (name,json.dumps(f["geometry"]),json.dumps(snapshot["regions"].get(name,{}))))
if __name__=="__main__": main()
