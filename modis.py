"""ORNL DAAC MOD11A2.061: tek piksel, kalite bitleri ve gözlem tarihleri."""
import argparse
import concurrent.futures
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
import pandas as pd

POINTS = {"Antalya": (36.89, 30.70), "Erzurum": (39.90, 41.27), "İstanbul": (41.02, 28.97)}
TEMPORAL_POINTS = {**POINTS,"İstanbul": (41.05,28.86)}
API = "https://modis.ornl.gov/rst/api/v1/MOD11A2/subset"

def download(task):
    city, year, first, last = task
    lat, lon = TEMPORAL_POINTS[city]
    cache = Path("cache/modis") / city / f"{year}-{first}.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        obj = json.loads(cache.read_text(encoding="utf8"))
    else:
        query = dict(latitude=lat, longitude=lon, startDate=f"A{year}{first:03d}",
                     endDate=f"A{year}{last:03d}", kmAboveBelow=0, kmLeftRight=0)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(API+"?"+urllib.parse.urlencode(query),timeout=65) as stream:
                    obj = json.load(stream)
                if not isinstance(obj, dict) or "subset" not in obj:
                    raise ValueError(str(obj)[:150])
                cache.write_text(json.dumps(obj))
                break
            except Exception:
                if attempt == 2: raise
                time.sleep(2**attempt)
    dates = {}
    for record in obj["subset"]:
        dates.setdefault(record["calendar_date"], {})[record["band"]] = record["data"][0]
    rows = []
    for date, bands in dates.items():
        raw, qc = bands["LST_Day_1km"], int(bands["QC_Day"])
        good = 7500 <= raw <= 65535 and (qc & 3) <= 1 and ((qc >> 2) & 3) == 0 and (qc >> 6) <= 1
        rows.append(dict(city=city,date=date,lat=lat,lon=lon,lst=raw*.02-273.15 if good else None,
                         qc=qc,raw=raw,product="MOD11A2",pixel_x=obj.get("xllcorner"),pixel_y=obj.get("yllcorner")))
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cities",nargs="+",choices=list(POINTS),default=list(POINTS))
    p.add_argument("--start",type=int,default=2003)
    p.add_argument("--end",type=int,default=2025)
    p.add_argument("--workers",type=int,default=4)
    args=p.parse_args()
    tasks=[(c,y,d,min(d+72,361)) for c in args.cities for y in range(args.start,args.end+1) for d in range(1,362,80)]
    records=[]
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        for rows in pool.map(download,tasks): records.extend(rows)
    frame=pd.DataFrame(records).sort_values(["city","date"])
    frame.to_csv("data/modis.csv",index=False)
    print(frame.groupby("city").lst.agg(["size","count"]))

if __name__=="__main__": main()
