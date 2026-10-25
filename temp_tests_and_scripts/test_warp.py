import os
from osgeo import gdal
import math
from dotenv import load_dotenv

load_dotenv()

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lon_deg, lat_deg

gdal.SetConfigOption("AWS_REGION", "us-east-1")

# The exact path the backend generated for the VRT
source_file = "/vsis3/catastro-ortofotos/complementos/orto_chacarita.vrt"

# z,x,y from the failing network request in the screenshot
z, x, y = 15, 9150, 16506

minx, miny = num2deg(x, y + 1, z)
maxx, maxy = num2deg(x + 1, y, z)

gdal.UseExceptions()

# First test: without srcSRS (what caused the 500 error)
warp_opts_no_src = gdal.WarpOptions(
    format="MEM",
    outputBounds=[minx, miny, maxx, maxy],
    outputBoundsSRS="EPSG:4326",
    dstSRS="EPSG:3857",
    width=256,
    height=256,
    resampleAlg="nearest",
    srcNodata="0",
    dstAlpha=True,
    warpOptions=["NUM_THREADS=ALL_CPUS"],
    multithread=True
)

try:
    print("Testing Warp WITHOUT srcSRS...")
    ds = gdal.Warp("", source_file, options=warp_opts_no_src)
    if ds is None:
        print(f"GDAL Warp failed: {gdal.GetLastErrorMsg()}")
    else:
        print("Success! (Without srcSRS)")
except Exception as e:
    print(f"Exception WITHOUT srcSRS: {e}")

# Second test: with srcSRS (what was originally there)
warp_opts_with_src = gdal.WarpOptions(
    format="MEM",
    outputBounds=[minx, miny, maxx, maxy],
    outputBoundsSRS="EPSG:4326",
    srcSRS="EPSG:32717",
    dstSRS="EPSG:3857",
    width=256,
    height=256,
    resampleAlg="nearest",
    srcNodata="0",
    dstAlpha=True,
    warpOptions=["NUM_THREADS=ALL_CPUS"],
    multithread=True
)

try:
    print("\nTesting Warp WITH srcSRS...")
    ds = gdal.Warp("", source_file, options=warp_opts_with_src)
    if ds is None:
        print(f"GDAL Warp failed: {gdal.GetLastErrorMsg()}")
    else:
        print("Success! (With srcSRS)")
except Exception as e:
    print(f"Exception WITH srcSRS: {e}")
