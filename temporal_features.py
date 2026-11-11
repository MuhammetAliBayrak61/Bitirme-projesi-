"""Çok değişkenli pilot: tarihsel MOD09A1 indisleri, ERA5-Land ve Skadi."""
import concurrent.futures
import json
import time
from pathlib import Path
import urllib.request
import urllib.parse
import numpy as np
import pandas as pd
from modis import TEMPORAL_POINTS as POINTS
from topography import sample
def cached(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url,timeout=75) as r: obj=json.load(r)
                if not isinstance(obj,dict) or obj.get("error"): raise ValueError(str(obj)[:180])
                path.write_text(json.dumps(obj));break
            except Exception:
                if attempt==2: raise
                time.sleep(3**attempt)
    return json.loads(path.read_text(encoding="utf8"))
def get_opt(job):
    city,y,d=job
    lat,lon=POINTS[city]
    q=dict(latitude=lat,longitude=lon,startDate=f"A{y}{d:03}",endDate=f"A{y}{min(d+72,361):03}",kmAboveBelow=0,kmLeftRight=0)
    obj=cached("https://modis.ornl.gov/rst/api/v1/MOD09A1/subset?"+urllib.parse.urlencode(q),Path("cache/opt")/(f"{city}-{lat}-{lon}" if city=="İstanbul" else city)/f"{y}-{d}.json")
    by={}
    for rec in obj["subset"]:
        by.setdefault(rec["calendar_date"],{})[rec["band"]]=rec["data"][0]
    rows=[]
    for date,r in by.items():
        state=int(next(v for k,v in r.items() if "state" in k.lower()))
        qa=int(next(v for k,v in r.items() if "qc" in k.lower()))
        good=state&7==0 and state&(1<<10|1<<12|1<<13|1<<15)==0 and qa&3==0
        red,nir,swir=[next(v for k,v in r.items() if f"b0{i}" in k) for i in (1,2,6)]
        def ratio(a,b):
            return (a-b)/(a+b) if good and min(a,b)>=0 and max(a,b)<=16000 and a+b else np.nan
        rows.append(dict(date=date,city=city,ndvi=ratio(nir,red),ndbi=ratio(swir,nir)))
    return rows
def get_weather(job):
    city,y=job
    lat,lon=POINTS[city]
    q=dict(latitude=lat,longitude=lon,start_date=f"{y}-01-01",end_date=f"{y}-12-31",models="era5_land",
           hourly="temperature_2m,dew_point_2m",timezone="GMT")
    obj=cached("https://archive-api.open-meteo.com/v1/archive?"+urllib.parse.urlencode(q),Path("cache/weather")/city/f"{y}.json")
    hourly=pd.DataFrame(obj["hourly"]).rename(columns={"temperature_2m":"air","dew_point_2m":"dew"})
    doy=pd.to_datetime(hourly.time).dt.dayofyear
    hourly["date"]=(pd.Timestamp(y,1,1)+pd.to_timedelta(((doy-1)//8)*8,unit="D")).dt.strftime("%Y-%m-%d")
    return hourly.groupby("date")[["air","dew"]].mean().reset_index().assign(city=city)
def main():
    jobs=[(c,y) for c in POINTS for y in range(2018,2026)]
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        optical=list(pool.map(get_opt,[(c,y,d) for c,y in jobs for d in range(1,362,80)]))
    opt=pd.DataFrame([r for chunk in optical for r in chunk])
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        weather=pd.concat(pool.map(get_weather,jobs))
    df=pd.read_csv("data/modis.csv").query("date >= '2018'").merge(opt,on=["city","date"],how="left",validate="one_to_one").merge(weather,on=["city","date"],how="left",validate="one_to_one")
    for city,(lat,lon) in POINTS.items():
        df.loc[df.city==city,["height","slope"]]=sample(lat,lon)
    df.to_csv("data/modis-multi.csv",index=False)
if __name__=="__main__": main()
