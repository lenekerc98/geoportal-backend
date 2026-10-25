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

# Get a tile that is completely outside the TIF (to guarantee nodata)
z, x, y = 20, 146520, 264208
minx, miny = num2deg(x, y + 1, z)
maxx, maxy = num2deg(x + 1, y, z)

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

ds = gdal.Warp("", source_file, options=warp_opts)

band_count = ds.RasterCount
print("Warped RasterCount:", band_count)

band_list = None
if band_count > 4:
    band_list = [1, 2, 3, band_count]  # Asume RGB + Alpha (al final)
elif band_count == 4:
    band_list = [1, 2, 3, 4] # Asume RGBA
elif band_count == 3:
    band_list = [1, 2, 3] # Asume RGB

png_opts = gdal.TranslateOptions(format="PNG", bandList=band_list)
png_ds = gdal.Translate("test_final.png", ds, options=png_opts)

print("PNG generated. Checking alpha...")
alpha = png_ds.GetRasterBand(4).ReadAsArray()
print("Unique alpha values in PNG:", set(alpha.flatten()))
