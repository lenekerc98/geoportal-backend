import os
from osgeo import gdal
from dotenv import load_dotenv

load_dotenv()
gdal.SetConfigOption("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
gdal.SetConfigOption("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID"))
gdal.SetConfigOption("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY"))
gdal.SetConfigOption("AWS_NO_SIGN_REQUEST", "NO")
gdal.UseExceptions()

ds = gdal.Open("/vsis3/catastro-ortofotos/ortofotos/orto_los_angeles.tif")
gt = ds.GetGeoTransform()
width = ds.RasterXSize
height = ds.RasterYSize

minx = gt[0]
maxy = gt[3]
maxx = minx + gt[1] * width
miny = maxy + gt[5] * height

print(f"BBox UTM 17S:")
print(f"MinX: {minx}, MaxX: {maxx}")
print(f"MinY: {miny}, MaxY: {maxy}")
