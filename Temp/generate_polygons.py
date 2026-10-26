import os
import shutil
import zipfile
from osgeo import ogr, gdal
import shapely.wkb
from shapely.ops import unary_union
from shapely.geometry import Polygon

ogr.UseExceptions()
gdal.SetConfigOption("SHAPE_ENCODING", "UTF-8")

src_shp = r"C:\Users\leneker\Downloads\LIND_CANTONAL\LIND_CANTONAL.shp"
src_prj = r"C:\Users\leneker\Downloads\LIND_CANTONAL\LIND_CANTONAL.prj"

ds = ogr.Open(src_shp)
layer = ds.GetLayer()
srs = layer.GetSpatialRef()
defn = layer.GetLayerDefn()

geoms = []
existing_features = []

for feat in layer:
    geom = feat.GetGeometryRef()
    poly = shapely.wkb.loads(bytes(geom.ExportToWkb()))
    geoms.append(poly)
    
    attrs = {
        'CODPRO': feat.GetField('CODPRO'),
        'PROVINCIA': feat.GetField('PROVINCIA'),
        'CODCAN': feat.GetField('CODCAN'),
        'CANTON': feat.GetField('CANTON'),
        'AREA': feat.GetField('AREA')
    }
    existing_features.append((attrs, geom.Clone()))

u = unary_union(geoms)

main_hole = None
max_area = 0
for interior in u.interiors:
    p = Polygon(interior)
    if p.area > max_area:
        max_area = p.area
        main_hole = p

urdaneta_ogr_geom = ogr.CreateGeometryFromWkb(shapely.wkb.dumps(main_hole))

urdaneta_attrs = {
    'CODPRO': '12',
    'PROVINCIA': 'LOS RIOS',
    'CODCAN': '535',
    'CANTON': 'URDANETA',
    'AREA': round(main_hole.area / 10000.0, 4)
}

output_dir = r"c:\LNCZ\proyecto-catastro-2026\backend\Temp\output_shapes"
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir, exist_ok=True)

driver = ogr.GetDriverByName("ESRI Shapefile")

def create_shapefile(filepath, feature_list):
    if os.path.exists(filepath):
        driver.DeleteDataSource(filepath)
    out_ds = driver.CreateDataSource(filepath, options=["ENCODING=UTF-8"])
    out_layer = out_ds.CreateLayer(os.path.splitext(os.path.basename(filepath))[0], srs, geom_type=ogr.wkbPolygon, options=["ENCODING=UTF-8"])
    
    for i in range(defn.GetFieldCount()):
        f_defn = defn.GetFieldDefn(i)
        out_layer.CreateField(f_defn)
        
    out_defn = out_layer.GetLayerDefn()
    for attrs, geom in feature_list:
        new_feat = ogr.Feature(out_defn)
        for k, v in attrs.items():
            new_feat.SetField(k, v)
        new_feat.SetGeometry(geom)
        out_layer.CreateFeature(new_feat)
        new_feat = None
        
    out_ds = None
    
    base = os.path.splitext(filepath)[0]
    if os.path.exists(src_prj):
        shutil.copy(src_prj, base + ".prj")
    with open(base + ".cpg", "w", encoding="utf-8") as f:
        f.write("UTF-8")

# 1. Standalone Urdaneta shapefile
create_shapefile(os.path.join(output_dir, "URDANETA_CANTONAL.shp"), [(urdaneta_attrs, urdaneta_ogr_geom)])

# 2. Complete LIND_CANTONAL
all_features = existing_features + [(urdaneta_attrs, urdaneta_ogr_geom)]
create_shapefile(os.path.join(output_dir, "LIND_CANTONAL_COMPLETO.shp"), all_features)

# 3. Zip archives
def zip_shapefile(base_name, target_zip):
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            fpath = os.path.join(output_dir, base_name + ext)
            if os.path.exists(fpath):
                z.write(fpath, arcname=base_name + ext)
    print(f"Zipped -> {target_zip}")

dest_dirs = [
    r"c:\LNCZ\proyecto-catastro-2026",
    r"C:\Users\leneker\Downloads"
]

for d in dest_dirs:
    zip_shapefile("URDANETA_CANTONAL", os.path.join(d, "URDANETA_CANTONAL.zip"))
    zip_shapefile("LIND_CANTONAL_COMPLETO", os.path.join(d, "LIND_CANTONAL_COMPLETO.zip"))

print("DONE_UTF8")
