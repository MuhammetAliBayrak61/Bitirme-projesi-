"""Hedef döneme göre bağımsız ayrım, geçmişten özellik üretimi ve eşleşmiş test."""
import os
os.environ.setdefault("KERAS_BACKEND","jax")
import argparse
from pathlib import Path
import json
import joblib
import keras
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from spatial_train import metrics

def calendar(year):
    return pd.DatetimeIndex([pd.Timestamp(y,1,1)+pd.Timedelta(days=k) for y in range(2003,year+2) for k in range(0,361,8)])
def samples(df,features,cutoff,window):
    seq,targets,meta=[],[],[]
    for city,part in df.groupby("city"):
        dates=calendar(part.date.dt.year.max())
        data=part.set_index("date").reindex(dates)
        # Eşit aralıklı MODIS dönemlerini koru; maskeler eksikliği modele bildirir.
        observed=data[features].notna().astype(float)
        values=data[features].ffill(limit=3)
        last=dates.get_loc(part.date.max())
        for i in range(window-1,last+1):
            if not observed.lst.iloc[max(0,i-3):i+1].any(): continue
            past=np.c_[values.iloc[i-window+1:i+1],observed.iloc[i-window+1:i+1]]
            for h in range(1,5):
                target=i+h
                if target<46: continue
                y=data.lst.iloc[target]
                if pd.isna(y) and i!=last: continue
                seq.append(np.column_stack([past,np.full(window,h/4)]))
                targets.append(y)
                meta.append((city,dates[i],dates[target],h,data.lst.iloc[target-46],i==last))
    return np.array(seq,dtype="float32"),np.array(targets),pd.DataFrame(meta,columns=["city","origin","date","h","baseline","latest"])
def run(path,mode,windows,epochs):
    df=pd.read_csv(path,parse_dates=["date"]).sort_values(["city","date"])
    if df.duplicated(["city","date"]).any(): raise ValueError("Bir il ve tarih için tek seri gerekli.")
    features=["lst"] if mode=="uni" else ["lst","ndvi","ndbi","height","slope","air","dew"]
    endtrain=2021 if mode=="uni" else 2022
    df=df[df.date.dt.year.between(2003 if mode=="uni" else 2018,2025)]
    winners={}
    validation=[]
    results=Path("results")
    for w in windows:
        X,y,m=samples(df,features,endtrain,w)
        year=m.date.dt.year
        train=(year<=endtrain)&np.isfinite(y)
        val=year.between(endtrain+1,2023)&np.isfinite(y)&m.baseline.notna()
        if not train.any() or not val.any(): raise ValueError("Eğitim/doğrulama gözlemi eksik.")
        width=X.shape[-1]
        scaler=StandardScaler().fit(X[train].reshape(-1,width))
        X=np.nan_to_num(scaler.transform(X.reshape(-1,width)).reshape(X.shape)).astype("float32")
        center=float(y[train].mean()); scale=float(y[train].std()) or 1.
        for name in ["XGBoost","LSTM"]:
            if name=="XGBoost":
                model=XGBRegressor(n_estimators=120,max_depth=3,learning_rate=.06,n_jobs=2,random_state=42)
                z=X.reshape(len(X),-1)
                model.fit(z[train],(y[train]-center)/scale)
            else:
                keras.utils.set_random_seed(42)
                model=keras.Sequential([keras.Input(shape=(w,width)),keras.layers.LSTM(16),keras.layers.Dense(1)])
                model.compile(optimizer="adam",loss="mse")
                z=X
                model.fit(z[train],(y[train]-center)/scale,validation_data=(z[val],(y[val]-center)/scale),
                          epochs=epochs,batch_size=96,verbose=0,callbacks=[keras.callbacks.EarlyStopping(patience=3,restore_best_weights=True)])
            def predict(mask):
                p=model.predict(z[mask],verbose=0) if name=="LSTM" else model.predict(z[mask])
                return p.ravel()*scale+center
            score=metrics(y[val],predict(val))["rmse"]
            validation.append(dict(model=name,window=w,validation_rmse=score))
            if score>=winners.get(name,(np.inf,))[0]: continue
            # Model seçimi yalnızca doğrulama puanını okur.
            pathbase=f"models/{mode}-{name}"
            if name=="LSTM": model.save(pathbase+".keras")
            else: model.save_model(pathbase+".json")
            joblib.dump(dict(scaler=scaler,center=center,scale=scale,window=w,features=features),pathbase+"-preprocess.joblib")
            mask=(year.between(2024,2025)&np.isfinite(y)&m.baseline.notna())|m.latest
            out=m[mask].copy()
            out["actual"]=y[mask]; out["prediction"]=predict(mask); out["model"]=name
            winners[name]=(score,out)
    pred=pd.concat([r[1] for r in winners.values()])
    pred[pred.latest].to_csv(results/f"future-{mode}.csv",index=False)
    test=pred[pred.date.dt.year.between(2024,2025)&pred.actual.notna()&pred.baseline.notna()].copy()
    baseline=test[test.model=="XGBoost"].copy()
    baseline["model"]="SeasonalNaive"; baseline["prediction"]=baseline.baseline
    test=pd.concat([test,baseline],ignore_index=True)
    test.to_csv(results/f"backtest-{mode}.csv",index=False)
    report=[]
    for (city,h,model),g in test.groupby(["city","h","model"]):
        ref=metrics(g.actual,g.baseline)["rmse"]
        stats=metrics(g.actual,g.prediction)
        report.append(dict(city=city,h=int(h),model=model,change_pct=100*(1-stats["rmse"]/ref) if ref else None,**stats))
    (results/f"temporal-{mode}.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    pd.DataFrame(validation).to_csv(results/f"validation-{mode}.csv",index=False)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="data/modis.csv")
    p.add_argument("--mode",choices=["uni","multi"],default="uni")
    p.add_argument("--windows",type=int,nargs="+",default=[8,16,24])
    p.add_argument("--epochs",type=int,default=15)
    a=p.parse_args(); run(a.data,a.mode,a.windows,a.epochs)
