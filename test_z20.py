import os
import time
import math
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

# User coordinate: 680592, 9841915
# Let's project it to Lat/Lng to find the XYZ tile for Z=20
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

print(f"Testing tile Z={z}, X={x}, Y={y}")

source_file = "/vsis3/catastro-ortofotos/complementos/orto_los_angeles.vrt"

warp_opts = gdal.WarpOptions(
    format="MEM",
    outputBounds=[minx, miny, maxx, maxy],
    outputBoundsSRS="EPSG:4326",
    srcSRS="EPSG:32717",
    dstSRS="EPSG:3857",
    width=256,
    height=256,
    resampleAlg="nearest",
    srcNodata="0 0 0",
    dstAlpha=True
)

t0 = time.time()
ds = gdal.Warp("", source_file, options=warp_opts)
t1 = time.time()
print(f"Warp took {t1-t0} seconds")

if ds:
    print("RasterCount:", ds.RasterCount)
else:
    print("DS is None!")
