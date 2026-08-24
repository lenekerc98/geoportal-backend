geoportal_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Geoportal\Geoportal.jsx'

with open(geoportal_path, 'r', encoding='utf-8') as f:
    gp_content = f.read()

target = '''            {showAtlasModal && importedShapes && (
        <ShapefileAtlasModal
          geoJsonData={importedShapes}
          fileName={atlasFileName || "Shapefile"}
          onClose={() => setShowAtlasModal(false)}
          onSavedPredio={() => {
            fetchPredios();
            fetchLineas();
            fetchVertices();
          }}
        />
      )}'''

replacement = '''      {showAtlasModal && importedShapes && (
        <ShapefileAtlasModal
          geoJsonData={importedShapes}
          fileName={atlasFileName || "Shapefile"}
          onClose={() => setShowAtlasModal(false)}
          onSavedPredio={() => {
            fetchMapData();
          }}
        />
      )}'''

if target in gp_content:
    gp_content = gp_content.replace(target, replacement)
    with open(geoportal_path, 'w', encoding='utf-8') as f:
        f.write(gp_content)
    print("Fixed onSavedPredio in Geoportal.jsx successfully.")
else:
    # Try more flexible replacement
    import re
    pattern = r'onSavedPredio=\{\(\)\s*=>\s*\{\s*fetchPredios\(\);\s*fetchLineas\(\);\s*fetchVertices\(\);\s*\}\}'
    if re.search(pattern, gp_content):
        gp_content = re.sub(pattern, 'onSavedPredio={() => { fetchMapData(); }}', gp_content)
        with open(geoportal_path, 'w', encoding='utf-8') as f:
            f.write(gp_content)
        print("Regex replaced onSavedPredio successfully.")
    else:
        print("Target not found.")
