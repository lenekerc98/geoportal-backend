import os
import math
from osgeo import gdal
from dotenv import load_dotenv

load_dotenv()
gdal.SetConfigOption("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
gdal.SetConfigOption("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID"))
gdal.SetConfigOption("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY"))
gdal.SetConfigOption("AWS_NO_SIGN_REQUEST", "NO")
gdal.SetConfigOption("GDAL_CACHEMAX", "256")
gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
gdal.SetConfigOption("VSI_CACHE", "TRUE")
gdal.SetConfigOption("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff,.vrt,.ovr")
gdal.UseExceptions()

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lon_deg, lat_deg

source_file = "/vsis3/catastro-ortofotos/complementos/orto_los_angeles.vrt"

print("Generating tile z=19, x=146520, y=264208")
minx, miny = num2deg(146520, 264208 + 1, 19)
maxx, maxy = num2deg(146520 + 1, 264208, 19)

warp_opts = gdal.WarpOptions(
    format="MEM",
    outputBounds=[minx, miny, maxx, maxy],
    outputBoundsSRS="EPSG:4326",
    srcSRS="EPSG:32717",
    dstSRS="EPSG:3857",
    width=256,
    height=256,
    resampleAlg="nearest",
    srcNodata="0",
    dstAlpha=True
)

import time
t0 = time.time()
print("Starting Warp...")
ds = gdal.Warp("", source_file, options=warp_opts)
print(f"Warp finished in {time.time()-t0:.2f}s")
if ds:
    print("Raster count:", ds.RasterCount)
else:
    print("Warp failed.")
