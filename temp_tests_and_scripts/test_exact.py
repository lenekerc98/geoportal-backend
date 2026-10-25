import math
from osgeo import gdal

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lon_deg, lat_deg

def generate_tile_bytes(z: int, x: int, y: int, source_file: str):
    gdal.UseExceptions()
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
    
    ds = gdal.Warp("", source_file, options=warp_opts)
    if ds is None:
        print(f"GDAL Warp failed for {source_file}: {gdal.GetLastErrorMsg()}")
        return None
        
    band_count = ds.RasterCount
    band_list = None
    if band_count > 4:
        band_list = [1, 2, 3, band_count]  
    elif band_count == 4:
        band_list = [1, 2, 3, 4] 
    elif band_count == 3:
        band_list = [1, 2, 3] 
        
    png_opts = gdal.TranslateOptions(format="PNG", bandList=band_list)
    png_path = f"/vsimem/tile_{z}_{x}_{y}_{abs(hash(source_file))}.png"
    png_ds = gdal.Translate(png_path, ds, options=png_opts)
    if png_ds is None:
        print(f"GDAL Translate failed: {gdal.GetLastErrorMsg()}")
        return None
    png_ds = None 
    
    f = gdal.VSIFOpenL(png_path, "rb")
    if f is None: 
        print(f"VSIFOpenL failed: {gdal.GetLastErrorMsg()}")
        return None
    gdal.VSIFSeekL(f, 0, 2)
    size = gdal.VSIFTellL(f)
    gdal.VSIFSeekL(f, 0, 0)
    png_data = gdal.VSIFReadL(1, size, f)
    gdal.VSIFCloseL(f)
    gdal.Unlink(png_path)
    ds = None
    
    return bytes(png_data)

z, x, y = 14, 4578, 8255
source1 = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Complementos\ortofotos.vrt"
source2 = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Ortofotos\Ortofoto_Completa.tif"

print("Testing VRT:")
res1 = generate_tile_bytes(z, x, y, source1)
print(f"Result VRT: {'OK, size: '+str(len(res1)) if res1 else 'None'}")

print("Testing TIF directly:")
res2 = generate_tile_bytes(z, x, y, source2)
print(f"Result TIF: {'OK, size: '+str(len(res2)) if res2 else 'None'}")
