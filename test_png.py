import math
from osgeo import gdal

gdal.UseExceptions()

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lon_deg, lat_deg

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

# Let's get the z,x,y for the user's coordinate: 670416.74, 9840829.56
# But those are UTM17S!
# Let's create a coordinate transformation
from osgeo import osr
proj_utm = osr.SpatialReference()
proj_utm.ImportFromEPSG(32717)
proj_wgs84 = osr.SpatialReference()
proj_wgs84.ImportFromEPSG(4326)
proj_wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

transform = osr.CoordinateTransformation(proj_utm, proj_wgs84)
lon, lat, _ = transform.TransformPoint(670416.74, 9840829.56)

print(f"User coords in WGS84: {lat}, {lon}")

for z in [14, 18, 19, 20]:
    x, y = deg2num(lat, lon, z)
    minx, miny = num2deg(x, y + 1, z)
    maxx, maxy = num2deg(x + 1, y, z)
    
    warp_opts = gdal.WarpOptions(
        format="MEM",
        outputBounds=[minx, miny, maxx, maxy],
        outputBoundsSRS="EPSG:4326",
        srcSRS="EPSG:32717",
        dstSRS="EPSG:3857",
        width=256,
        height=256,
        resampleAlg="nearest",
        srcNodata="0",
        dstAlpha=True
    )
    
    source_file = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Complementos\ortofotos.vrt"
    ds = gdal.Warp("", source_file, options=warp_opts)
    if ds is not None:
        # Check if it's all empty
        band = ds.GetRasterBand(1)
        stats = band.GetStatistics(0, 1)
        print(f"Z={z} X={x} Y={y} -> Min: {stats[0]}, Max: {stats[1]}")
    else:
        print(f"Z={z} X={x} Y={y} -> Failed Warp")
