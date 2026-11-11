from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from xgboost import XGBRegressor

def metrics(y,p):
    return dict(n=len(y),mae=float(mean_absolute_error(y,p)),rmse=float(np.sqrt(mean_squared_error(y,p))),r2=float(r2_score(y,p)) if len(y)>1 and np.std(y)>0 else None)
def main():
    df=pd.concat([pd.read_csv(f) for f in sorted(Path("data").glob("spatial-*.csv"))],ignore_index=True)
    df["block"]=df.city+"_"+np.floor(df.lat/.015).astype(str)+"_"+np.floor(df.lon/.02).astype(str)
    inputs=[]
    for tag,fields in [("A",["ndvi","ndbi"]),("B",["height","slope"]),("C",["built"]),("D",["air","dew"])]:
        inputs.extend(fields)
        if any(x not in df for x in inputs): break
        rows=df.dropna(subset=inputs+["lst"])
        records=[]
        for city in sorted(rows.city.unique()):
            test=rows[rows.city==city]
            train=rows[rows.city!=city]
            folds=list(GroupKFold(n_splits=3).split(train,groups=train.block))
            for name,options in [
                ("LinearRegression",[LinearRegression()]),
                ("RandomForest",[RandomForestRegressor(n_estimators=80,min_samples_leaf=k,random_state=42,n_jobs=2) for k in [3,10]]),
                ("XGBoost",[XGBRegressor(max_depth=k,n_estimators=80,learning_rate=.06,n_jobs=2,random_state=42) for k in [2,4]])]:
                X,y=train[inputs],train.lst
                def score(model):
                    return np.mean([mean_squared_error(y.iloc[b],model.fit(X.iloc[a],y.iloc[a]).predict(X.iloc[b])) for a,b in folds])
                best=min(options,key=score).fit(X,y)
                pred=best.predict(test[inputs])
                joblib.dump(best,Path("models")/f"{tag}-{city}-{name}.joblib",compress=3)
                records.append(dict(city=city,model=name,group=tag,**metrics(test.lst,pred)))
                part=test[["city","date","lat","lon","lst","block"]].copy()
                part["pred"]=pred
                part.to_csv(f"results/points-{tag}-{city}-{name}.csv",index=False)
        Path(f"results/spatial-{tag}.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf8")
if __name__=="__main__": main()
