from osgeo import ogr
import shapely.wkb
from shapely.ops import unary_union, polygonize
from shapely.geometry import Polygon, MultiPolygon

ogr.UseExceptions()
ds = ogr.Open(r"C:\Users\leneker\Downloads\LIND_CANTONAL\LIND_CANTONAL.shp")
layer = ds.GetLayer()

geoms = []
for feat in layer:
    geom = feat.GetGeometryRef()
    poly = shapely.wkb.loads(bytes(geom.ExportToWkb()))
    geoms.append(poly)

u = unary_union(geoms)
print("Union type:", u.geom_type)
if u.geom_type == 'Polygon':
    print("Number of interior rings in union:", len(u.interiors))
    for idx, interior in enumerate(u.interiors):
        hole_poly = Polygon(interior)
        print(f"Hole {idx}: area = {hole_poly.area:.2f} m2 ({hole_poly.area/10000:.2f} ha), bounds = {hole_poly.bounds}")
elif u.geom_type == 'MultiPolygon':
    for p_idx, p in enumerate(u.geoms):
        print(f"Polygon {p_idx}: area={p.area:.2f}, holes={len(p.interiors)}")
        for idx, interior in enumerate(p.interiors):
            hole_poly = Polygon(interior)
            print(f"  Hole {idx}: area = {hole_poly.area:.2f} m2 ({hole_poly.area/10000:.2f} ha), bounds = {hole_poly.bounds}")
