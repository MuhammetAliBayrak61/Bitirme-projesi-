import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from forecast import calendar,samples

class CalendarTests(unittest.TestCase):
    def test_year_boundary(self):
        periods=calendar(2025)
        i=periods.get_loc("2025-12-27")
        self.assertEqual(str(periods[i+1].date()),"2026-01-01")
        self.assertEqual(str(periods[i-46].date()),"2024-12-26")

    def test_no_future_features_and_preserve_gap(self):
        dates=calendar(2005)[:100]
        df=pd.DataFrame(dict(city="A",date=dates,lst=np.arange(100,dtype=float)))
        origin=dates[65]
        df.loc[64,"lst"]=np.nan
        X,y,m=samples(df,["lst"],2004,8)
        changed=df.copy()
        changed.loc[changed.date>origin,"lst"]+=100
        X2,y2,m2=samples(changed,["lst"],2004,8)
        at=(m.origin==origin)&(m.h==2)
        np.testing.assert_equal(X[at],X2[(m2.origin==origin)&(m2.h==2)])
        self.assertEqual(X[at][0,-2,1],0)
        self.assertEqual(y2[at][0]-y[at][0],100)

    def test_disjoint_spatial_outputs(self):
        for path in Path("results").glob("points-*.csv"):
            df=pd.read_csv(path)
            self.assertEqual(df.city.nunique(),1)
            self.assertTrue(df.city.iloc[0] in path.name)
            self.assertFalse(df.duplicated(["date","lat","lon"]).any())

    def test_saved_models_reproduce_published_forecasts(self):
        from predict import forecast
        for mode,filename in [("uni","modis.csv"),("multi","modis-multi.csv")]:
            output=forecast("data/"+filename,mode)
            expected=pd.read_csv(f"results/future-{mode}.csv",parse_dates=["date"])
            output["date"]=pd.to_datetime(output["date"])
            joined=expected.merge(output,on=["city","date","model","h"],validate="one_to_one")
            self.assertEqual(len(joined),len(expected))
            np.testing.assert_allclose(joined.prediction_x,joined.prediction_y,atol=.0001)

if __name__=="__main__":unittest.main()
