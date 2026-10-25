import os
from osgeo import gdal
from dotenv import load_dotenv

load_dotenv()
gdal.SetConfigOption("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
gdal.SetConfigOption("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID"))
gdal.SetConfigOption("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY"))
gdal.SetConfigOption("AWS_NO_SIGN_REQUEST", "NO")
gdal.UseExceptions()

ds = gdal.Open("/vsis3/catastro-ortofotos/ortofotos/orto_chacarita.tif")
gt = ds.GetGeoTransform()
print(f"Chacarita MinX: {gt[0]}")

ds2 = gdal.Open("/vsis3/catastro-ortofotos/ortofotos/orto_zapotal_viejo.tif")
gt2 = ds2.GetGeoTransform()
print(f"Zapotal Viejo MinX: {gt2[0]}")

ds3 = gdal.Open("/vsis3/catastro-ortofotos/ortofotos/orto_zapotal_nuevo.tif")
gt3 = ds3.GetGeoTransform()
print(f"Zapotal Nuevo MinX: {gt3[0]}")
