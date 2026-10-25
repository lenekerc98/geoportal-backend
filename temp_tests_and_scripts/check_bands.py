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
print("RasterCount:", ds.RasterCount)
for i in range(1, ds.RasterCount + 1):
    band = ds.GetRasterBand(i)
    color = band.GetColorInterpretation()
    nodata = band.GetNoDataValue()
    print(f"Band {i}: Color={color}, NoData={nodata}")
