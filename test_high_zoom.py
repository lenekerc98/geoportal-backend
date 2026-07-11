import math
from osgeo import gdal

gdal.UseExceptions()

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lon_deg, lat_deg

z, x, y = 14, 4578, 8255
source_file = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Complementos\ortofotos.vrt"

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
    srcNodata="0",
    dstAlpha=True,
    warpOptions=["NUM_THREADS=ALL_CPUS", "GDAL_CACHEMAX=2048"],
    multithread=True
)

print(f"Testing tile {z}/{x}/{y}")
ds = gdal.Warp("", source_file, options=warp_opts)

if ds is None:
    print("Warp returned None!")
else:
    print(f"Warp OK. Bands: {ds.RasterCount}")
    band_count = ds.RasterCount
    band_list = [1, 2, 3]
    if band_count >= 4:
        band_list = [1, 2, 3, band_count]
    
    png_path = f"/vsimem/tile_{z}_{x}_{y}.png"
    png_opts = gdal.TranslateOptions(format="PNG", bandList=band_list)
    png_ds = gdal.Translate(png_path, ds, options=png_opts)
    if png_ds is None:
        print("Translate failed!")
    else:
        f = gdal.VSIFOpenL(png_path, "rb")
        if f:
            data = gdal.VSIFReadL(1, 1000000, f)
            print(f"PNG generated successfully, size: {len(data)} bytes")
            gdal.VSIFCloseL(f)
        else:
            print("VSIFOpenL failed!")

