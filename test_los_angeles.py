import os
import math
from osgeo import gdal
from dotenv import load_dotenv
import urllib.request

load_dotenv()

gdal.SetConfigOption("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
gdal.SetConfigOption("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID"))
gdal.SetConfigOption("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY"))
gdal.UseExceptions()

z = 16
x = 18318
y = 33030
source_file = "/vsis3/catastro-ortofotos/complementos/orto_los_angeles.vrt"

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lon_deg, lat_deg)

minlon, minlat = num2deg(x, y + 1, z)
maxlon, maxlat = num2deg(x + 1, y, z)

print(f"BBox requested: minlon={minlon}, minlat={minlat}, maxlon={maxlon}, maxlat={maxlat}")
print(f"Opening {source_file}...")
ds = gdal.Open(source_file)
gt = ds.GetGeoTransform()
xmin = gt[0]
ymax = gt[3]
xmax = xmin + ds.RasterXSize * gt[1] + ds.RasterYSize * gt[2]
ymin = ymax + ds.RasterXSize * gt[4] + ds.RasterYSize * gt[5]
print(f"Native BBox: {xmin}, {ymin}, {xmax}, {ymax}")

warp_opts_4326 = gdal.WarpOptions(format="MEM", dstSRS="EPSG:4326")
ds_4326 = gdal.Warp("", ds, options=warp_opts_4326)
if ds_4326:
    gt2 = ds_4326.GetGeoTransform()
    x1 = gt2[0]
    y2 = gt2[3]
    x2 = x1 + ds_4326.RasterXSize * gt2[1]
    y1 = y2 + ds_4326.RasterYSize * gt2[5]
    print(f"BBox of image in 4326: minlon={x1}, minlat={y1}, maxlon={x2}, maxlat={y2}")

warp_opts = gdal.WarpOptions(
    format="MEM",
    outputBounds=[minlon, minlat, maxlon, maxlat],
    outputBoundsSRS="EPSG:4326",
    dstSRS="EPSG:3857",
    width=256,
    height=256,
    resampleAlg="nearest",
    srcNodata="0",
    dstAlpha=True
)

out_ds = gdal.Warp("", ds, options=warp_opts)
if out_ds:
    print("Warp successful. Writing to tile.png...")
    gdal.Translate("tile.png", out_ds, format="PNG")
    print(f"Size of tile.png: {os.path.getsize('tile.png')} bytes")
else:
    print("Warp failed.")
