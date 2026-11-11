"""Pano için kaynağı izlenebilir, ölçüm ve tahminleri ayrı tutan veri paketi."""
import json
from pathlib import Path
import pandas as pd

def records(frame):
    return json.loads(frame.to_json(orient="records",double_precision=4,force_ascii=False))
def main():
    features=json.loads(Path("data/provinces.geojson").read_text(encoding="utf8"))["features"]
    regions={}
    for file in Path("data").glob("spatial-*.csv"):
        df=pd.read_csv(file)
        for city,g in df.groupby("city"):
            r=regions.setdefault(city,{})
            r.setdefault("cells",[]).extend(records(g[["date","lat","lon","lst","ndvi","ndbi"]].dropna()))
            r["candidates"]=r.get("candidates",0)+len(g)
    for file in sorted(Path("results").glob("spatial-*.json")):
        for row in json.loads(file.read_text(encoding="utf8")): regions[row["city"]].setdefault("spatial",[]).append(row)
    df=pd.read_csv("data/modis.csv")
    for city,g in df.groupby("city"):
        r=regions.setdefault(city,{})
        r["history"]=records(g[["date","lst"]]);r["location"]=records(g[["lat","lon"]].iloc[:1])[0]
    for mode in ["uni","multi"]:
        metrics_file=Path(f"results/temporal-{mode}.json")
        if not metrics_file.exists(): continue
        for row in json.loads(metrics_file.read_text(encoding="utf8")):
            row["mode"]=mode
            regions[row["city"]].setdefault("scores",[]).append(row)
        for city,g in pd.read_csv(f"results/future-{mode}.csv").groupby("city"):
            values=g[["date","h","origin","model","prediction"]].copy()
            baseline=g[g.model=="XGBoost"][["date","h","origin","baseline"]].dropna().rename(columns={"baseline":"prediction"}).assign(model="SeasonalNaive")
            regions[city].setdefault("future",[]).extend(records(pd.concat([values,baseline]).assign(mode=mode)))
    path=Path("web/src/snapshot.json")
    path.write_text(json.dumps(dict(features=features,regions=regions),ensure_ascii=False,separators=(",",":"),allow_nan=False),encoding="utf8")
if __name__=="__main__": main()
