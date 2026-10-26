from osgeo import ogr

for name, path in [
    ("URDANETA_CANTONAL", r"c:\LNCZ\proyecto-catastro-2026\backend\Temp\output_shapes\URDANETA_CANTONAL.shp"),
    ("LIND_CANTONAL_COMPLETO", r"c:\LNCZ\proyecto-catastro-2026\backend\Temp\output_shapes\LIND_CANTONAL_COMPLETO.shp")
]:
    ds = ogr.Open(path)
    layer = ds.GetLayer()
    print("=" * 60)
    print(f"Layer: {name}")
    print(f"  Features: {layer.GetFeatureCount()}")
    print(f"  CRS: {layer.GetSpatialRef().GetName() if layer.GetSpatialRef() else 'None'}")
    for f in layer:
        geom = f.GetGeometryRef()
        print(f"  FID {f.GetFID()}: {f.GetField('CANTON')} ({f.GetField('PROVINCIA')}) - Area: {f.GetField('AREA')} ha | Geom Valid: {geom.IsValid()}")
