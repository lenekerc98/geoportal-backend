import os

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Geoportal\Geoportal.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                  let coordsText = '';
                  if (feature.geometry && feature.geometry.coordinates) {
                      const ring = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : feature.geometry.coordinates;
                      ring.forEach(pt => {
                          const utm = proj4('EPSG:4326', 'EPSG:32717', [pt[0], pt[1]]);
                          coordsText += ${utm[0].toFixed(2)} 
;
                      });
                  }
                  setTempPredioFormData({ geometry: feature, latlng: selectionContextMenu.latlng, geom_text: coordsText, es_utm: true });"""

replacement = """                  let coordsText = '';
                  if (feature.geometry && feature.geometry.coordinates) {
                      const ring = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : feature.geometry.coordinates;
                      ring.forEach(pt => {
                          const utm = proj4('EPSG:4326', 'EPSG:32717', [pt[0], pt[1]]);
                          coordsText += `${utm[0].toFixed(2)} ${utm[1].toFixed(2)}\\n`;
                      });
                  }
                  setTempPredioFormData({ geometry: feature, latlng: selectionContextMenu.latlng, geom_text: coordsText, es_utm: true });"""

if target in content:
    content = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("FIX_SUCCESS")
else:
    # Try line-based fix if exact whitespace differs
    print("Target not found by exact string, trying fallback line fix...")
    lines = content.split('\n')
    for i in range(len(lines)):
        if "coordsText += ${utm[0].toFixed(2)}" in lines[i]:
            lines[i] = "                          coordsText += `${utm[0].toFixed(2)} ${utm[1].toFixed(2)}\\n`;"
            if i + 1 < len(lines) and lines[i+1].strip() == ';':
                lines[i+1] = ""
            break
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("FALLBACK_SUCCESS")
