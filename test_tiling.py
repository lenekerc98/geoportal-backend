from osgeo import gdal
ds = gdal.Open(r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Ortofotos\Ortofoto_Completa.tif")
print(ds.GetMetadata("IMAGE_STRUCTURE"))
