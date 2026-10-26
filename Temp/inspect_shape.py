import os
import sys
from osgeo import ogr, osr

shp_path = r"C:\Users\leneker\Downloads\LIND_CANTONAL\LIND_CANTONAL.shp"
if not os.path.exists(shp_path):
    print("File not found:", shp_path)
    sys.exit(1)

ds = ogr.Open(shp_path)
if ds is None:
    print("Could not open shapefile")
    sys.exit(1)

layer = ds.GetLayer()
print("Layer name:", layer.GetName())
print("Feature count:", layer.GetFeatureCount())
sref = layer.GetSpatialRef()
print("Spatial Ref:", sref.ExportToWkt()[:150] if sref else "None")

defn = layer.GetLayerDefn()
fields = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
print("Fields:", fields)

for i in range(layer.GetFeatureCount()):
    feat = layer.GetFeature(i)
    if not feat:
        continue
    geom = feat.GetGeometryRef()
    if geom:
        print(f"FID {feat.GetFID()}: type={geom.GetGeometryName()}, subgeoms/rings={geom.GetGeometryCount()}, area={geom.GetArea():.2f}")
        for j in range(geom.GetGeometryCount()):
            sub = geom.GetGeometryRef(j)
            print(f"   sub[{j}]: type={sub.GetGeometryName()}, points={sub.GetPointCount()}, subcount={sub.GetGeometryCount()}")
    attrs = {f: feat.GetField(f) for f in fields}
    print(f"   attrs: {attrs}")
