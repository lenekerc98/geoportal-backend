import os
from osgeo import gdal

f1 = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Ortofotos\Ortofoto_Completa.tif"
f2 = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Complementos\ortofotos.vrt"

print(f"Exists f1: {os.path.exists(f1)}")
if os.path.exists(f1):
    ds1 = gdal.Open(f1)
    print(f"Open f1: {ds1 is not None}")

print(f"Exists f2: {os.path.exists(f2)}")
if os.path.exists(f2):
    ds2 = gdal.Open(f2)
    print(f"Open f2: {ds2 is not None}")
    if ds2 is not None:
        file_list = ds2.GetFileList()
        print(f"VRT File list: {file_list}")
        for fp in file_list:
            print(f"  {fp} exists? {os.path.exists(fp)}")
