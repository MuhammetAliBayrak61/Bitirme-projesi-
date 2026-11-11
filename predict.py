"""Kayıtlı modellerle son giriş döneminden sonraki dört MODIS kompozitini tahmin et."""
import argparse
import os
os.environ.setdefault("KERAS_BACKEND","jax")
from pathlib import Path
import joblib
import keras
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from forecast import calendar

def forecast(path,mode):
    frame=pd.read_csv(path,parse_dates=["date"])
    out=[]
    for name in ["XGBoost","LSTM"]:
        base="models/"+mode+"-"+name
        meta=joblib.load(base+"-preprocess.joblib")
        if name=="LSTM": model=keras.models.load_model(base+".keras")
        else:
            model=XGBRegressor()
            model.load_model(base+".json")
        for city,g in frame.groupby("city"):
            last=g.date.max()
            dates=calendar(last.year)
            i=dates.get_loc(last)
            f=meta["features"]; w=meta["window"]
            series=g.set_index("date").reindex(dates)[f]
            if not series.lst.iloc[i-3:i+1].notna().any(): continue
            window=series.iloc[i-w+1:i+1]
            v=series.ffill(limit=3).iloc[i-w+1:i+1]
            for h in range(1,5):
                x=np.c_[v,window.notna().astype(float),np.full(w,h/4)]
                x=np.nan_to_num(meta["scaler"].transform(x.astype("float32"))).astype("float32")
                pred=model.predict(x[None,:,:],verbose=0) if name=="LSTM" else model.predict(x.reshape(1,-1))
                out.append(dict(city=city,origin=last.date(),date=dates[i+h].date(),h=h,model=name,prediction=float(pred.ravel()[0])*meta["scale"]+meta["center"]))
    return pd.DataFrame(out)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("csv");p.add_argument("--mode",default="uni",choices=["uni","multi"])
    p.add_argument("--output",default="results/predictions.csv")
    a=p.parse_args();forecast(a.csv,a.mode).to_csv(a.output,index=False)
