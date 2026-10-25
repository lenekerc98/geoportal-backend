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
inv_gt = gdal.InvGeoTransform(gt)
px, py = gdal.ApplyGeoTransform(inv_gt, 600810, 9842137)
print("Pixel X:", px, "Pixel Y:", py)
if 0 <= px < ds.RasterXSize and 0 <= py < ds.RasterYSize:
    r = ds.GetRasterBand(1).ReadAsArray(int(px), int(py), 1, 1)[0][0]
    g = ds.GetRasterBand(2).ReadAsArray(int(px), int(py), 1, 1)[0][0]
    b = ds.GetRasterBand(3).ReadAsArray(int(px), int(py), 1, 1)[0][0]
    a = ds.GetRasterBand(4).ReadAsArray(int(px), int(py), 1, 1)[0][0]
    print(f"Pixel RGB: ({r}, {g}, {b}), Alpha: {a}")
else:
    print("Out of bounds")
