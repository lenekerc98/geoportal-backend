import re
import sys

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Geoportal\Geoportal.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscamos la asignación actual en el menú contextual
old_code = '''setTempPredioFormData({ geometry: feature, latlng: selectionContextMenu.latlng });
                  setIsAddingPredio(true);
                  setSelectionContextMenu(null);'''

new_code = '''// Extraer coordenadas de la feature GeoJSON a texto UTM para la tabla
                  let coordsText = '';
                  if (feature.geometry && feature.geometry.coordinates) {
                      const ring = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : feature.geometry.coordinates;
                      ring.forEach(pt => {
                          const utm = proj4('EPSG:4326', 'EPSG:32717', [pt[0], pt[1]]);
                          coordsText += `${utm[0].toFixed(2)} ${utm[1].toFixed(2)}\\n`;
                      });
                  }
                  
                  setTempPredioFormData({ 
                      geometry: feature, 
                      latlng: selectionContextMenu.latlng,
                      geom_text: coordsText,
                      es_utm: true
                  });
                  setIsAddingPredio(true);
                  setSelectionContextMenu(null);'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed context menu assignment.")
else:
    print("Could not find the target code. Maybe it was already modified or has different indentation.")
