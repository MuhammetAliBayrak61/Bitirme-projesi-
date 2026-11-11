"""Eşleştirilmiş RMSE farkı. Negatif fark aday model lehine."""
from pathlib import Path
import numpy as np
import pandas as pd

def interval(df, block):
    agg=df.assign(a=(df.prediction-df.actual)**2,b=(df.baseline-df.actual)**2).groupby(block).agg(
        a=("a","sum"),b=("b","sum"),n=("a","size"))
    if len(agg)<3: return (len(agg),np.nan,np.nan)
    samples=agg.to_numpy()[np.random.default_rng(42).integers(0,len(agg),(1000,len(agg)))].sum(axis=1)
    delta=np.sqrt(samples[:,0]/samples[:,2])-np.sqrt(samples[:,1]/samples[:,2])
    return (len(agg),*np.quantile(delta,[.025,.975]))

def main():
    out=[]
    for file in Path("results").glob("backtest-*.csv"):
        df=pd.read_csv(file,parse_dates=["date"])
        df["block"]=(df.date-pd.Timestamp("2024-01-01")).dt.days//32
        for (city,h,model),g in df.groupby(["city","h","model"]):
            out.append((file.stem,city,h,model,*interval(g,"block")))
    for file in Path("results").glob("points-*-LinearRegression.csv"):
        baseline=pd.read_csv(file).rename(columns={"pred":"baseline","lst":"actual"})
        for name in ["RandomForest","XGBoost"]:
            candidate=pd.read_csv(str(file).replace("LinearRegression",name)).rename(columns={"pred":"prediction"})
            data=baseline.merge(candidate[["lat","lon","date","prediction"]],on=["lat","lon","date"],validate="one_to_one")
            out.append((file.stem,data.city.iloc[0],0,name,*interval(data,"block")))
    pd.DataFrame(out,columns=["experiment","city","h","model","blocks","delta_rmse_low","delta_rmse_high"]).to_csv("results/intervals.csv",index=False)
if __name__=="__main__": main()
