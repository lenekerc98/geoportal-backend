from osgeo import ogr
import shapely.wkb
from shapely.ops import unary_union
from shapely.geometry import Polygon

ogr.UseExceptions()
ds = ogr.Open(r"C:\Users\leneker\Downloads\LIND_CANTONAL\LIND_CANTONAL.shp")
layer = ds.GetLayer()

geoms = []
for feat in layer:
    geom = feat.GetGeometryRef()
    poly = shapely.wkb.loads(bytes(geom.ExportToWkb()))
    geoms.append(poly)

u = unary_union(geoms)
# Hole 0 is the largest hole
main_hole = None
max_area = 0
for interior in u.interiors:
    p = Polygon(interior)
    if p.area > max_area:
        max_area = p.area
        main_hole = p

print("Main hole found!")
print("Area:", main_hole.area)
print("Is valid?", main_hole.is_valid)
print("Point count:", len(main_hole.exterior.coords))
print("Bounds:", main_hole.bounds)
