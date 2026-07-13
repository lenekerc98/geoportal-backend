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

def tile_bounds_web_mercator(x, y, z):
    R = 6378137.0 
    origin_shift = 2.0 * math.pi * R / 2.0
    initial_resolution = 2.0 * math.pi * R / 256.0
    res = initial_resolution / (2.0 ** z)
    
    minx = (x * 256.0) * res - origin_shift
    maxy = origin_shift - (y * 256.0) * res
    maxx = ((x + 1) * 256.0) * res - origin_shift
    miny = origin_shift - ((y + 1) * 256.0) * res
    return minx, miny, maxx, maxy

source_file = "/vsis3/catastro-ortofotos/complementos/orto_los_angeles.vrt"

# Use the EXACT XYZ that corresponds to the center of Los Angeles at Z=20
# Lat/Lng: -1.428, -79.387
lat = -1.428
lon = -79.387
z = 20
lat_rad = math.radians(lat)
n = 2.0 ** z
x = int((lon + 180.0) / 360.0 * n)
y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

print(f"Tile Z={z} X={x} Y={y}")

minx, miny, maxx, maxy = tile_bounds_web_mercator(x, y, z)
print(f"Web Mercator Bounds: {minx}, {miny}, {maxx}, {maxy}")

warp_opts = gdal.WarpOptions(
    format="MEM",
    outputBounds=[minx, miny, maxx, maxy],
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
band = ds.GetRasterBand(1)
arr = band.ReadAsArray()
print(f"Band 1 Unique values:", np.unique(arr)[:10])
