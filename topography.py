"""AWS Terrain Tiles / Skadi HGT yüksekliklerini hücrelere ekler."""
import gzip
import urllib.request
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd

@lru_cache(8)
def tile(lat,lon):
    name=f"N{lat:02}E{lon:03}"
    path=Path("cache/height")/(name+".hgt.gz")
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(f"https://elevation-tiles-prod.s3.amazonaws.com/skadi/N{lat:02}/{name}.hgt.gz",timeout=90) as r:
            path.write_bytes(r.read())
    data=np.frombuffer(gzip.decompress(path.read_bytes()),dtype=">i2")
    return data.reshape((int(np.sqrt(data.size)),)*2)
def sample(lat,lon):
    north,east=int(np.floor(lat)),int(np.floor(lon))
    arr=tile(north,east); n=arr.shape[0]-1
    y=round((north+1-lat)*n); x=round((lon-east)*n)
    dy=111320/n; dx=dy*np.cos(np.deg2rad(lat))
    ry=max(1,round(150/dy)); rx=max(1,round(150/dx))
    block=arr[max(0,y-ry):min(n+1,y+ry+1),max(0,x-rx):min(n+1,x+rx+1)].astype(float)
    block[block==-32768]=np.nan
    gy,gx=np.gradient(block,dy,dx)
    return np.nanmean(block),np.nanmean(np.rad2deg(np.arctan(np.hypot(gx,gy))))
if __name__=="__main__":
    for path in Path("data").glob("spatial-*.csv"):
        df=pd.read_csv(path)
        df[["height","slope"]]=[sample(row.lat,row.lon) for row in df.itertuples()]
        df.to_csv(path,index=False)
