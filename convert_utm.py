import os
from osgeo import osr

srs = osr.SpatialReference()
srs.ImportFromEPSG(32717)

srs_geo = osr.SpatialReference()
srs_geo.ImportFromEPSG(4326)

ct = osr.CoordinateTransformation(srs, srs_geo)
lon1, lat1, _ = ct.TransformPoint(679408, 9842137)
lon2, lat2, _ = ct.TransformPoint(600810, 9842137)

print(f"Orthophoto (679408): Lon {lon1}, Lat {lat1}")
print(f"User Vector (600810): Lon {lon2}, Lat {lat2}")
