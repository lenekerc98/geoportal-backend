import os
import math
import numpy as np
from osgeo import gdal
from dotenv import load_dotenv

load_dotenv()
gdal.SetConfigOption("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
gdal.SetConfigOption("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID"))
gdal.SetConfigOption("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY"))
gdal.SetConfigOption("AWS_NO_SIGN_REQUEST", "NO")
gdal.UseExceptions()

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lon_deg, lat_deg

source_file = "/vsis3/catastro-ortofotos/complementos/orto_los_angeles.vrt"

# Get a valid tile in the center of Los Angeles
from osgeo import osr
srs = osr.SpatialReference()
srs.ImportFromEPSG(32717)
srs_geo = osr.SpatialReference()
srs_geo.ImportFromEPSG(4326)
ct = osr.CoordinateTransformation(srs, srs_geo)
lon, lat, _ = ct.TransformPoint(680592, 9841915)

def deg2num(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = int((lon_deg + 180.0) / 360.0 * n)
  ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
  return xtile, ytile

z = 20
x, y = deg2num(lat, lon, z)

minx, miny = num2deg(x, y + 1, z)
maxx, maxy = num2deg(x + 1, y, z)

ct_4326_3857 = osr.CoordinateTransformation(srs_geo, osr.SpatialReference().SetFromUserInput('EPSG:3857'))
minx_3857, miny_3857, _ = ct_4326_3857.TransformPoint(miny, minx)
maxx_3857, maxy_3857, _ = ct_4326_3857.TransformPoint(maxy, maxx)

warp_opts = gdal.WarpOptions(
    format="MEM",
    outputBounds=[minx_3857, miny_3857, maxx_3857, maxy_3857],
    srcSRS="EPSG:32717",
    dstSRS="EPSG:3857",
    width=256,
    height=256,
    resampleAlg="nearest",
    srcNodata="0 0 0",
    dstAlpha=True
)

ds = gdal.Warp("", source_file, options=warp_opts)

print("Warped RasterCount:", ds.RasterCount)
for i in range(1, ds.RasterCount + 1):
    band = ds.GetRasterBand(i)
    arr = band.ReadAsArray()
    print(f"Band {i} Unique values:", np.unique(arr)[:10])

