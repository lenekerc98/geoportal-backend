import os
import math
from osgeo import gdal
import traceback

os.environ['PROJ_LIB'] = r"C:\Program Files\QGIS 4.0.2\share\proj"
gdal.SetConfigOption('PROJ_LIB', r"C:\Program Files\QGIS 4.0.2\share\proj")

def tile_to_bbox_webmercator(x, y, z):
    ORIGIN_SHIFT = 2 * math.pi * 6378137.0 / 2.0
    INITIAL_RESOLUTION = 2 * math.pi * 6378137.0 / 256.0
    res = INITIAL_RESOLUTION / (2 ** z)
    xmin = x * 256 * res - ORIGIN_SHIFT
    ymin = ORIGIN_SHIFT - (y + 1) * 256 * res
    xmax = (x + 1) * 256 * res - ORIGIN_SHIFT
    ymax = ORIGIN_SHIFT - y * 256 * res
    return (xmin, ymin, xmax, ymax)

try:
    gdal.UseExceptions()
    bbox = tile_to_bbox_webmercator(9146, 16515, 15)
    VRT_FILE = r"C:\LNCZ\proyecto-catastro-2026\backend\ortofotos.vrt"
    warp_opts = gdal.WarpOptions(format="MEM", dstSRS="EPSG:3857", outputBounds=bbox, width=256, height=256, resampleAlg="bilinear")
    print("Iniciando Warp...")
    ds = gdal.Warp("", VRT_FILE, options=warp_opts)
    print("Warp terminado. DS:", ds)
except Exception as e:
    print("Error GDAL:")
    traceback.print_exc()
