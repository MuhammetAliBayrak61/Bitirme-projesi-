"""Airflow 2.10 DAG; LST_ROOT proje kökü, LST_PYTHON araştırma ortamındaki Python."""
import os
import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator
root=os.environ["LST_ROOT"]
python=os.environ["LST_PYTHON"]
with DAG("turkiye_lst_pilot",start_date=pendulum.datetime(2025,1,1,tz="UTC"),
         schedule=None,catchup=False,max_active_runs=1,default_args={"retries":1}) as dag:
    def task(name,script):
        return BashOperator(task_id=name,bash_command='"$LST_PYTHON" scripts/'+script,cwd=root,append_env=True,
                            env={"LST_PYTHON":python})
    spatial=task("landsat_sentinel","spatial_data.py")
    terrain=task("topografya","topography.py")
    train=task("mekansal_egitim","spatial_train.py")
    modis=task("modis_indir","modis.py")
    forecast=task("zamansal_egitim","forecast.py")
    features=task("cevre_serileri","temporal_features.py")
    multi=task("cok_degiskenli_egitim","forecast.py --mode multi --data data/modis-multi.csv")
    report=task("guven_araliklari","confidence.py")
    snapshot=task("pano_verisi","snapshot.py")
    spatial >> terrain >> train >> report
    modis >> forecast >> report >> snapshot
    [modis,terrain] >> features >> multi >> report
