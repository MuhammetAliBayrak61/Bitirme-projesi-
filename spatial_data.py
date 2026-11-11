"""Landsat sıcaklığı ve Sentinel-2 indislerini ortak 300 m UTM hücrelerinde eşleştir."""
import concurrent.futures
import json
import os
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform, transform_bounds, reproject, Resampling
from rasterio.transform import from_origin
from modis import POINTS

PC="https://planetarycomputer.microsoft.com/api"
AWS="https://earth-search.aws.element84.com/v1"
def fetch(url):
    with urllib.request.urlopen(url,timeout=45) as f: return json.load(f)
def search(base,coll,lon,lat):
    query=dict(collections=coll,bbox=f"{lon-.01},{lat-.01},{lon+.01},{lat+.01}",
               datetime="2023-08-01T00:00:00Z/2023-08-31T23:59:59Z",limit=100)
    return fetch(base+"/search?"+urllib.parse.urlencode(query))["features"]
def day(scene): return date.fromisoformat(scene["properties"]["datetime"][:10])

def extract(city):
    lat,lon=POINTS[city]
    lands=search(PC+"/stac/v1","landsat-c2-l2",lon,lat)
    sents=search(AWS,"sentinel-2-l2a",lon,lat)
    pairs=[(a,b) for a in lands for b in sents if a["id"].startswith(("LC08_L2SP","LC09_L2SP"))
           and abs((day(a)-day(b)).days)<=3]
    pairs=[p for p in pairs if max(t["properties"]["eo:cloud_cover"] for t in p)<25] or pairs
    a,b=min(pairs,key=lambda pair: (abs((day(pair[0])-day(pair[1])).days),
               sum(t["properties"]["eo:cloud_cover"] for t in pair)))
    token=fetch(PC+"/sas/v1/token/landsat-c2-l2")["token"]
    crs=f"EPSG:{32601+int((lon+180)//6)}"
    x,y=transform("EPSG:4326",crs,[lon],[lat])
    left=int(x[0]//300)*300-3000
    top=int(y[0]//300)*300+3000
    extent=(left,top-6000,left+6000,top)
    def load_band(args):
        scene,band,size=args
        meta=scene["assets"][band]
        url=meta["href"]+("?"+token if scene is a else "")
        out=np.zeros((6000//size,6000//size),np.float32)
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",CPL_VSIL_CURL_USE_HEAD="NO",
                          GDAL_HTTP_TIMEOUT="45",GDAL_HTTP_MAX_RETRY="2",GDAL_HTTP_PROXY=os.getenv("https_proxy","")):
            with rasterio.open(url) as src:
                bounds=transform_bounds(crs,src.crs,*extent)
                win=from_bounds(*(v+(-120 if i<2 else 120) for i,v in enumerate(bounds)),src.transform).round_offsets().round_lengths()
                data=src.read(1,window=win,boundless=True,fill_value=0)
                reproject(data,out,src_transform=src.window_transform(win),src_crs=src.crs,
                          dst_transform=from_origin(left,top,size,size),dst_crs=crs,resampling=Resampling.nearest)
        return out
    with concurrent.futures.ThreadPoolExecutor(5) as ex:
        thermal,qa,sat,red,nir,swir,scl=ex.map(load_band,[(a,"lwir11",30),(a,"qa_pixel",30),(a,"qa_radsat",30),
            (b,"red",20),(b,"nir",20),(b,"swir16",20),(b,"scl",20)])
    good=(thermal>0)&((qa.astype(int)&63)==0)&(sat==0)
    lst=np.where(good,thermal*.00341802+149-273.15,np.nan)
    clear=np.isin(scl,[4,5,6])&(red>0)&(nir>0)&(swir>0)
    def refl(values,key):
        m=b["assets"][key]["raster:bands"][0]
        # Earth Search COGs may have had the BOA offset applied by the publisher.
        return values*m.get("scale",.0001)+(0 if b["properties"].get("earthsearch:boa_offset_applied") else m.get("offset",0))
    red,nir,swir=(refl(v,k) for v,k in [(red,"red"),(nir,"nir"),(swir,"swir16")])
    def ratio(v,w):
        den=v+w
        return np.divide(v-w,den,out=np.full_like(v,np.nan),where=clear&(v>=0)&(w>=0)&(den>0))
    def cells(arr):
        n=arr.shape[0]//20
        blocks=arr.reshape(20,n,20,n)
        count=np.isfinite(blocks).sum((1,3))
        return np.nansum(blocks,(1,3))/np.maximum(count,1),count/n**2
    temp,tfrac=cells(lst)
    ndvi,vfrac=cells(ratio(nir,red))
    ndbi,bfrac=cells(ratio(swir,nir))
    row,col=np.indices((20,20))
    x=(left+300*col+150).ravel()
    y=(top-300*row-150).ravel()
    lons,lats=transform(crs,"EPSG:4326",x,y)
    df=pd.DataFrame(dict(city=city,date=day(a),sentinel_date=day(b),lat=lats,lon=lons,
        row=row.ravel(),col=col.ravel(),lst=temp.ravel(),ndvi=ndvi.ravel(),ndbi=ndbi.ravel(),
        thermal_fraction=tfrac.ravel(),optical_fraction=np.minimum(vfrac,bfrac).ravel(),
        landsat_scene=a["id"],sentinel_scene=b["id"]))
    for name,frac in [("lst","thermal_fraction"),("ndvi","optical_fraction"),("ndbi","optical_fraction")]:
        df.loc[df[frac]<.7,name]=np.nan
    df.to_csv(Path("data")/f"spatial-{city}.csv",index=False)
    print(city,len(df.dropna()),flush=True)
if __name__=="__main__":
    import sys
    for city in sys.argv[1:] or POINTS: extract(city)
