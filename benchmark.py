"""İsteğe bağlı eşdeğer il/yıl toplulaştırması. Süre okumayı ve sonuç almayı içerir."""
import argparse
import time
import pandas as pd
def main():
    p=argparse.ArgumentParser()
    p.add_argument("file"); p.add_argument("engine",choices=["pandas","spark"])
    a=p.parse_args(); start=time.perf_counter()
    if a.engine=="pandas":
        df=pd.read_csv(a.file,parse_dates=["date"])
        out=df.groupby(["city",df.date.dt.year.rename("year")]).lst.mean().reset_index()
    else:
        from pyspark.sql import SparkSession, functions as F
        spark=SparkSession.builder.master("local[*]").appName("LST").getOrCreate()
        df=spark.read.option("header",True).csv(a.file)
        out=df.groupBy("city",F.year("date").alias("year")).agg(F.avg(F.col("lst").cast("double")).alias("lst")).toPandas()
        spark.stop()
    seconds=time.perf_counter()-start
    out.sort_values(["city","year"]).to_csv("results/aggregation-"+a.engine+".csv",index=False)
    print(f"{a.engine}: {seconds:.3f} s, {len(out)} il-yıl.")
if __name__=="__main__": main()
