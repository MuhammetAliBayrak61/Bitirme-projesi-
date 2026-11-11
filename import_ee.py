"""Bir Earth Engine dışa aktarım klasörünü ayrı bir deney köküne alır."""
import argparse
from pathlib import Path
import pandas as pd

def main():
    p=argparse.ArgumentParser()
    p.add_argument("exports",type=Path)
    p.add_argument("experiment",type=Path)
    args=p.parse_args()
    if args.experiment.exists(): raise ValueError("Yeni bir deney dizini seçin.")
    tables={}
    for mode in ["temporal","spatial"]:
        files=sorted(args.exports.glob(mode+"-*.csv"))
        if not files: continue
        df=pd.concat([pd.read_csv(f) for f in files],ignore_index=True)
        required=["city","date","lst"]+(["lat","lon","ndvi","ndbi","height","slope","built","air","dew"] if mode=="spatial" else ["valid_fraction"])
        if set(required)-set(df.columns): raise ValueError(f"{mode} sütunları eksik.")
        if mode=="temporal":
            df.loc[df.valid_fraction.fillna(0)<.5,"lst"]=float("nan")
        key=["city","date"]+(["lat","lon"] if mode=="spatial" else [])
        if df.duplicated(key).any(): raise ValueError(f"{mode} içinde yinelenen kayıt")
        tables[mode]=df
    if not tables: raise ValueError("spatial-*.csv veya temporal-*.csv bulunamadı.")
    for folder in ["models","results","data"]: (args.experiment/folder).mkdir(parents=True)
    for mode,df in tables.items():
        if mode=="temporal": df.to_csv(args.experiment/"data/modis.csv",index=False)
        else:
            for city,g in df.groupby("city"): g.to_csv(args.experiment/f"data/spatial-{city}.csv",index=False)
if __name__=="__main__": main()
