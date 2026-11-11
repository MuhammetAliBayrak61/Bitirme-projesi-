from tempfile import TemporaryDirectory
from pathlib import Path
from urllib.request import urlretrieve
import json
import shapefile
from shapely.geometry import shape,mapping

def convert(archive):
    features=[]
    for r in shapefile.Reader(str(archive)).iterShapeRecords(fields=["adm0_a3","name_tr","name"]):
        if r.record["adm0_a3"]!="TUR": continue
        geom=shape(r.shape.__geo_interface__).simplify(.016,preserve_topology=True)
        features.append(dict(type="Feature",properties={"name":r.record["name_tr"] or r.record["name"]},geometry=mapping(geom)))
    assert len(features)==81
    Path("data/provinces.geojson").write_text(json.dumps(dict(type="FeatureCollection",features=features),ensure_ascii=False),encoding="utf8")
if __name__=="__main__":
    import sys
    with TemporaryDirectory() as tmp:
        archive=Path(tmp)/"admin.zip"
        if len(sys.argv)>1: archive=Path(sys.argv[1])
        else: urlretrieve("https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip",archive)
        convert(archive)
