import os
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

source_file = "/vsis3/catastro-ortofotos/complementos/orto_los_angeles.vrt"

# Get a tile that is partially out of bounds (an edge tile)
minx, miny = num2deg(18318, 33030 + 1, 16)
maxx, maxy = num2deg(18318 + 1, 33030, 16)

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
band_list = [1, 2, 3, band_count] if band_count >= 4 else [1, 2, 3]

png_opts = gdal.TranslateOptions(format="PNG", bandList=band_list)
gdal.Translate("test_edge.png", ds, options=png_opts)

# Now read the alpha channel of the generated PNG
png_ds = gdal.Open("test_edge.png")
alpha = png_ds.GetRasterBand(4).ReadAsArray()
unique_alpha = set(alpha.flatten())
print("Unique alpha values:", unique_alpha)
