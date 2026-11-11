"""EE batch exports. Drive klasöründeki CSV dosyalarını indirerek kullanın."""
import argparse
import json
import unicodedata
from pathlib import Path
import datetime as dt
import ee
PILOTS=["Istanbul","Erzurum","Antalya"]
def collection(name,area,start,end):
    return ee.ImageCollection(name).filterBounds(area).filterDate(start,end)
def land(img):
    qa=img.select("QA_PIXEL")
    return img.select("ST_B10").multiply(.00341802).subtract(124.15).rename("lst").updateMask(
        qa.bitwiseAnd(63).eq(0).And(img.select("QA_RADSAT").eq(0)).And(img.select("ST_B10").gt(0)))
def opt(img):
    scl=img.select("SCL")
    img=img.updateMask(scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)))
    return img.normalizedDifference(["B8","B4"]).rename("ndvi").addBands(
        img.normalizedDifference(["B11","B8"]).rename("ndbi"))
def composite(col,bands):
    blank=ee.Image.constant([0]*len(bands)).rename(bands).selfMask()
    return col.merge(ee.ImageCollection([blank])).median()
def mean300(img,src):
    fine=img.setDefaultProjection(src)
    avg=fine.reduceResolution(reducer=ee.Reducer.mean(),maxPixels=2048).reproject("EPSG:6933",None,300)
    valid=fine.mask().unmask(0).reduceResolution(reducer=ee.Reducer.mean(),maxPixels=2048).reproject("EPSG:6933",None,300)
    return avg.updateMask(valid.gte(.7))
def layers(area,start,end):
    s2=collection("COPERNICUS/S2_SR_HARMONIZED",area,start,end).map(opt)
    dem=ee.Image("USGS/SRTMGL1_003")
    dw=collection("GOOGLE/DYNAMICWORLD/V1",area,start,end).select("built")
    era=collection("ECMWF/ERA5_LAND/DAILY_AGGR",area,start,end)
    weather=era.select(["temperature_2m","dewpoint_temperature_2m"]).mean().subtract(273.15).rename(["air","dew"])
    optical=composite(s2,["ndvi","ndbi"])
    # Equal-area source grid before fine-to-coarse aggregation.
    base=mean300(optical,ee.Projection("EPSG:6933").atScale(20))
    return base.addBands(mean300(dem.rename("height").addBands(ee.Terrain.slope(dem)),dem.projection())).addBands(
        mean300(composite(dw,["built"]),ee.Projection("EPSG:6933").atScale(10))).addBands(weather)
def spatial(region,city,year):
    start=dt.date(year,6,1)
    parts=[]
    while start < dt.date(year,9,1):
        end=min(start+dt.timedelta(days=8),dt.date(year,9,1))
        a,b=start.isoformat(),end.isoformat()
        lands=collection("LANDSAT/LC08/C02/T1_L2",region,a,b).merge(collection("LANDSAT/LC09/C02/T1_L2",region,a,b))
        target=composite(lands.filter(ee.Filter.eq("PROCESSING_LEVEL","L2SP")).map(land),["lst"])
        stack=mean300(target,ee.Projection("EPSG:6933").atScale(30)).addBands(layers(region,a,b)).addBands(ee.Image.pixelLonLat().rename(["lon","lat"]))
        parts.append(stack.sample(region=region,scale=300,projection="EPSG:6933",numPixels=2500,seed=43).map(
            lambda f,d=a:f.set({"date":d,"city":city})))
        start=end
    return ee.FeatureCollection(parts).flatten()
def temporal(region,city,year,with_features):
    mod=collection("MODIS/061/MOD11A2",region,f"{year}-01-01",f"{year+1}-01-01")
    def summarize(img):
        img=ee.Image(img)
        date=img.date()
        stop=ee.Date(ee.Number(date.advance(8,"day").millis()).min(ee.Date(f"{year+1}-01-01").millis()))
        qa=img.select("QC_Day")
        temp=img.select("LST_Day_1km").multiply(.02).subtract(273.15).rename("lst").updateMask(
            qa.bitwiseAnd(3).lte(1).And(qa.rightShift(2).bitwiseAnd(3).eq(0)).And(qa.rightShift(6).lte(1)))
        stack=temp.addBands(temp.mask().unmask(0).rename("valid_fraction"))
        if with_features: stack=stack.addBands(layers(region,date,stop))
        return ee.Feature(None,stack.reduceRegion(reducer=ee.Reducer.mean(),geometry=region,crs=img.select(0).projection(),
                scale=1000,maxPixels=1e9,tileScale=4)).set({"date":date.format("YYYY-MM-dd"),"city":city})
    return ee.FeatureCollection(mod.toList(46).map(summarize))
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--mode",choices=["spatial","temporal"],required=True)
    p.add_argument("--year",type=int,required=True)
    p.add_argument("--city",default="Antalya",help="Türkçe il adı veya ALL")
    args=p.parse_args()
    ee.Initialize(project=args.project)
    fc=json.loads(Path("data/provinces.geojson").read_text(encoding="utf8"))
    regions={f["properties"]["name"]:f["geometry"] for f in fc["features"]}
    cities=list(regions) if args.city=="ALL" else [args.city]
    for city in cities:
        if city not in regions: raise ValueError(f"Geçerli adlar: {list(regions)}")
        region=ee.Geometry(regions[city])
        table=(spatial(region,city,args.year) if args.mode=="spatial" else temporal(region,city,args.year,args.year>=2018))
        ascii_city=unicodedata.normalize("NFKD",city.replace("ı","i")).encode("ascii","ignore").decode()
        label=f"{args.mode}-{ascii_city}-{args.year}"
        task=ee.batch.Export.table.toDrive(collection=table,description=label,folder="LST_Turkiye",fileFormat="CSV")
        task.start()
        print(label,task.id,flush=True)
if __name__=="__main__": main()
