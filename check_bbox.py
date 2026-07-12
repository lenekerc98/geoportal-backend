import os
import math
from osgeo import gdal
from dotenv import load_dotenv

load_dotenv()

gdal.SetConfigOption("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
gdal.SetConfigOption("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID"))
gdal.SetConfigOption("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY"))

gdal.UseExceptions()

vrt_path = "/vsis3/catastro-ortofotos/complementos/orto_los_angeles.vrt"
print(f"Opening {vrt_path}...")
try:
    ds = gdal.Open(vrt_path)
    gt = ds.GetGeoTransform()
    print("GeoTransform:", gt)
    print("Size:", ds.RasterXSize, ds.RasterYSize)
    
    xmin = gt[0]
    ymax = gt[3]
    xmax = xmin + ds.RasterXSize * gt[1] + ds.RasterYSize * gt[2]
    ymin = ymax + ds.RasterXSize * gt[4] + ds.RasterYSize * gt[5]
    
    print(f"BBox in native CRS: minx={xmin}, miny={ymin}, maxx={xmax}, maxy={ymax}")
    
    # Try warp to EPSG:4326 to get lat/lon bounds
    warp_opts = gdal.WarpOptions(format="MEM", dstSRS="EPSG:4326")
    ds_wgs84 = gdal.Warp("", ds, options=warp_opts)
    if ds_wgs84:
        gt_ll = ds_wgs84.GetGeoTransform()
        ll_xmin = gt_ll[0]
        ll_ymax = gt_ll[3]
        ll_xmax = ll_xmin + ds_wgs84.RasterXSize * gt_ll[1] + ds_wgs84.RasterYSize * gt_ll[2]
        ll_ymin = ll_ymax + ds_wgs84.RasterXSize * gt_ll[4] + ds_wgs84.RasterYSize * gt_ll[5]
        print(f"BBox in EPSG:4326: minlon={ll_xmin}, minlat={ll_ymin}, maxlon={ll_xmax}, maxlat={ll_ymax}")
    else:
        print("Failed to warp to EPSG:4326")

except Exception as e:
    print(f"Error: {e}")
