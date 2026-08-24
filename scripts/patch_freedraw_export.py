import os

predio_form_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\MapViewer\PredioForm.jsx'
with open(predio_form_path, 'r', encoding='utf-8') as f:
    pf_content = f.read()

target_pf = '''  const [formData, setFormData] = useState({
    posesionario_id: initialData?.posesionario_id || '',
    cod_catastral: initialData?.cod_catastral || '',
    geom_geojson: initialData?.geom_text || formatInitialCoords(initialData?.geom_geojson),
  });
  const [colindantes, setColindantes] = useState([]);
  const [rumbosCustom, setRumbosCustom] = useState([]);'''

replacement_pf = '''  const [formData, setFormData] = useState({
    posesionario_id: initialData?.posesionario_id || '',
    cod_catastral: initialData?.cod_catastral || '',
    geom_geojson: initialData?.geom_text || (typeof initialData?.geom_geojson === 'string' ? initialData.geom_geojson : formatInitialCoords(initialData?.geom_geojson)) || '',
  });
  const [colindantes, setColindantes] = useState([]);
  const [rumbosCustom, setRumbosCustom] = useState([]);

  useEffect(() => {
    if (initialData) {
      const coords = initialData.geom_text || (typeof initialData.geom_geojson === 'string' ? initialData.geom_geojson : formatInitialCoords(initialData.geom_geojson)) || '';
      setFormData(prev => ({
        ...prev,
        posesionario_id: initialData.posesionario_id !== undefined ? initialData.posesionario_id : prev.posesionario_id,
        cod_catastral: initialData.cod_catastral !== undefined ? initialData.cod_catastral : prev.cod_catastral,
        geom_geojson: coords || prev.geom_geojson || ''
      }));
    }
  }, [initialData]);'''

if target_pf in pf_content:
    pf_content = pf_content.replace(target_pf, replacement_pf)
    with open(predio_form_path, 'w', encoding='utf-8') as f:
        f.write(pf_content)
    print("Updated PredioForm.jsx successfully.")
else:
    print("Target not found in PredioForm.jsx")

geoportal_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Geoportal\Geoportal.jsx'
with open(geoportal_path, 'r', encoding='utf-8') as f:
    gp_content = f.read()

# Helper export functions to insert before handleFeatureInteraction
export_funcs = '''  const getFeatureUTMCoords = (feature) => {
    proj4.defs("EPSG:32717", "+proj=utm +zone=17 +south +datum=WGS84 +units=m +no_defs");
    let rawCoords = [];
    if (feature.positions && feature.positions.length > 0) {
      rawCoords = feature.positions.map(p => {
        const lat = Array.isArray(p) ? p[0] : (p.lat !== undefined ? p.lat : p[0]);
        const lng = Array.isArray(p) ? p[1] : (p.lng !== undefined ? p.lng : p[1]);
        return { lat, lng };
      });
    } else if (feature.geometry && feature.geometry.coordinates) {
      const ring = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : feature.geometry.coordinates;
      rawCoords = ring.map(pt => ({ lng: pt[0], lat: pt[1] }));
    }
    return rawCoords.map(pt => {
      const utm = proj4('EPSG:4326', 'EPSG:32717', [pt.lng, pt.lat]);
      return [utm[0], utm[1]];
    });
  };

  const exportFeatureToShapefile = (feature) => {
    try {
      const utmCoords = getFeatureUTMCoords(feature);
      if (utmCoords.length === 0) {
        Swal.fire('Error', 'No hay coordenadas válidas para exportar.', 'error');
        return;
      }

      const typeName = feature.type || 'Polygon';
      let geojsonGeometry = null;

      if (typeName === 'Point') {
        geojsonGeometry = { type: 'Point', coordinates: utmCoords[0] };
      } else if (typeName === 'Line' || typeName === 'Polyline') {
        geojsonGeometry = { type: 'LineString', coordinates: utmCoords };
      } else {
        const closed = [...utmCoords];
        if (closed[0][0] !== closed[closed.length - 1][0] || closed[0][1] !== closed[closed.length - 1][1]) {
          closed.push([...closed[0]]);
        }
        geojsonGeometry = { type: 'Polygon', coordinates: [closed] };
      }

      const singleGeoJSON = {
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          properties: { id: feature.id, tipo: typeName },
          geometry: geojsonGeometry
        }]
      };

      const prj32717 = 'PROJCS["WGS_1984_UTM_Zone_17S",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",10000000.0],PARAMETER["Central_Meridian",-81.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]';
      const cleanName = `dibujo_${typeName.toLowerCase()}_${Date.now()}`;
      const options = {
        outputType: 'blob',
        compression: 'STORE',
        prj: prj32717,
        types: {
          point: `${cleanName}_pto`,
          multipoint: `${cleanName}_pto`,
          line: `${cleanName}_lin`,
          multiline: `${cleanName}_lin`,
          linestring: `${cleanName}_lin`,
          multilinestring: `${cleanName}_lin`,
          polygon: `${cleanName}_pol`,
          multipolygon: `${cleanName}_pol`
        }
      };

      Promise.resolve(shpwrite.zip(singleGeoJSON, options)).then(content => {
        if (content && typeof content.generateAsync === 'function') return content.generateAsync({ type: 'blob', compression: 'STORE' });
        if (content && typeof content.generate === 'function') return content.generate({ type: 'blob', compression: 'STORE' });
        return content;
      }).then(blob => {
        const finalBlob = blob instanceof Blob ? blob : new Blob([blob], { type: 'application/zip' });
        const url = URL.createObjectURL(finalBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${cleanName}.zip`;
        a.click();
        URL.revokeObjectURL(url);
        setToastMsg({ type: 'success', title: 'Exportado', message: 'Shapefile (.zip) descargado en EPSG:32717.' });
      }).catch(err => {
        console.error("SHP Export Error:", err);
        Swal.fire('Error', 'Error al exportar Shapefile: ' + err.message, 'error');
      });
    } catch (err) {
      Swal.fire('Error', 'Error al generar Shapefile: ' + err.message, 'error');
    }
  };

  const exportFeatureToCAD = (feature) => {
    try {
      const utmCoords = getFeatureUTMCoords(feature);
      if (utmCoords.length === 0) {
        Swal.fire('Error', 'No hay coordenadas válidas para exportar.', 'error');
        return;
      }

      const typeName = feature.type || 'Polygon';
      let dxf = "0\\nSECTION\\n2\\nHEADER\\n0\\nENDSEC\\n0\\nSECTION\\n2\\nTABLES\\n0\\nENDSEC\\n0\\nSECTION\\n2\\nBLOCKS\\n0\\nENDSEC\\n0\\nSECTION\\n2\\nENTITIES\\n";

      if (typeName === 'Point') {
        const [x, y] = utmCoords[0];
        dxf += `0\\nPOINT\\n8\\nCATASTRO_DIBUJO\\n10\\n${x.toFixed(4)}\\n20\\n${y.toFixed(4)}\\n30\\n0.0\\n`;
      } else if (typeName === 'Line' && utmCoords.length === 2) {
        const [x1, y1] = utmCoords[0];
        const [x2, y2] = utmCoords[1];
        dxf += `0\\nLINE\\n8\\nCATASTRO_DIBUJO\\n10\\n${x1.toFixed(4)}\\n20\\n${y1.toFixed(4)}\\n30\\n0.0\\n11\\n${x2.toFixed(4)}\\n21\\n${y2.toFixed(4)}\\n31\\n0.0\\n`;
      } else {
        const isClosed = typeName === 'Polygon' ? 1 : 0;
        dxf += `0\\nLWPOLYLINE\\n8\\nCATASTRO_DIBUJO\\n90\\n${utmCoords.length}\\n70\\n${isClosed}\\n`;
        utmCoords.forEach(([x, y]) => {
          dxf += `10\\n${x.toFixed(4)}\\n20\\n${y.toFixed(4)}\\n`;
        });
      }

      dxf += "0\\nENDSEC\\n0\\nEOF\\n";

      const blob = new Blob([dxf], { type: 'application/dxf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const filename = `dibujo_${typeName.toLowerCase()}_${Date.now()}.dxf`;
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      setToastMsg({ type: 'success', title: 'Exportado', message: 'Archivo CAD (.dxf) descargado en UTM 17S.' });
    } catch (err) {
      Swal.fire('Error', 'Error al generar CAD: ' + err.message, 'error');
    }
  };

  const handleFeatureInteraction = {'''

if 'const handleFeatureInteraction = {' in gp_content and 'const exportFeatureToCAD' not in gp_content:
    gp_content = gp_content.replace('const handleFeatureInteraction = {', export_funcs, 1)

# Replace the selectionContextMenu block
target_menu_pattern = '''        {selectionContextMenu && (
          <div 
            style={{ position: 'fixed', top: selectionContextMenu.y, left: selectionContextMenu.x, zIndex: 9999, background: '#fff', boxShadow: '0 4px 12px rgba(0,0,0,0.15)', borderRadius: '6px', padding: '5px', minWidth: '180px', border: '1px solid #e2e8f0' }}
            onMouseLeave={() => setSelectionContextMenu(null)}
          >
            <button 
               onClick={() => {
                 setSelectionContextMenu(null);
                 Swal.fire('Info', 'Exportación a GeoJSON en desarrollo...', 'info');
               }} 
               style={{ width: '100%', padding: '8px 12px', textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '13px', color: '#1e293b', borderBottom: '1px solid #f1f5f9' }}
               onMouseOver={(e) => e.target.style.background = '#f1f5f9'}
               onMouseOut={(e) => e.target.style.background = 'transparent'}
            >
              ⬇️ Exportar a GeoJSON
            </button>
            <button 
               onClick={() => {
                 const feature = freeDrawings.find(f => f.id === selectedFeatureIds[0]);
                 if (feature) {
                   
                  let coordsText = '';
                  if (feature.geometry && feature.geometry.coordinates) {
                      const ring = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : feature.geometry.coordinates;
                      ring.forEach(pt => {
                          const utm = proj4('EPSG:4326', 'EPSG:32717', [pt[0], pt[1]]);
                          coordsText += `${utm[0].toFixed(2)} ${utm[1].toFixed(2)}\\n`;
                      });
                  }
                  setTempPredioFormData({ geometry: feature, latlng: selectionContextMenu.latlng, geom_text: coordsText, es_utm: true });

                   setIsAddingPredio(true);
                   setSelectionContextMenu(null);
                 }
               }} 
               style={{ width: '100%', padding: '8px 12px', textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '13px', color: '#0369a1', fontWeight: '500' }}
               onMouseOver={(e) => e.target.style.background = '#e0f2fe'}
               onMouseOut={(e) => e.target.style.background = 'transparent'}
            >
              💾 Guardar en BD (Predio)
            </button>
          </div>
        )}'''

replacement_menu = '''        {selectionContextMenu && (
          <div 
            style={{ position: 'fixed', top: selectionContextMenu.y, left: selectionContextMenu.x, zIndex: 9999, background: '#fff', boxShadow: '0 4px 12px rgba(0,0,0,0.15)', borderRadius: '6px', padding: '5px', minWidth: '200px', border: '1px solid #e2e8f0' }}
            onMouseLeave={() => setSelectionContextMenu(null)}
          >
            <button 
               onClick={() => {
                 const feature = freeDrawings.find(f => f.id === selectedFeatureIds[0]);
                 if (feature) exportFeatureToShapefile(feature);
                 setSelectionContextMenu(null);
               }} 
               style={{ width: '100%', padding: '8px 12px', textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '13px', color: '#16a34a', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: '6px' }}
               onMouseOver={(e) => e.target.style.background = '#f0fdf4'}
               onMouseOut={(e) => e.target.style.background = 'transparent'}
            >
              📁 Exportar a Shapefile (.zip)
            </button>
            <button 
               onClick={() => {
                 const feature = freeDrawings.find(f => f.id === selectedFeatureIds[0]);
                 if (feature) exportFeatureToCAD(feature);
                 setSelectionContextMenu(null);
               }} 
               style={{ width: '100%', padding: '8px 12px', textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '13px', color: '#ea580c', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: '6px' }}
               onMouseOver={(e) => e.target.style.background = '#fff7ed'}
               onMouseOut={(e) => e.target.style.background = 'transparent'}
            >
              📐 Exportar a CAD (.dxf)
            </button>
            <button 
               onClick={() => {
                 const feature = freeDrawings.find(f => f.id === selectedFeatureIds[0]);
                 if (feature) {
                   proj4.defs("EPSG:32717", "+proj=utm +zone=17 +south +datum=WGS84 +units=m +no_defs");
                   let coordsText = '';
                   let rawCoords = [];
                   if (feature.positions && feature.positions.length > 0) {
                       rawCoords = feature.positions.map(p => {
                           const lat = Array.isArray(p) ? p[0] : (p.lat !== undefined ? p.lat : p[0]);
                           const lng = Array.isArray(p) ? p[1] : (p.lng !== undefined ? p.lng : p[1]);
                           return { lat, lng };
                       });
                   } else if (feature.geometry && feature.geometry.coordinates) {
                       const ring = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : feature.geometry.coordinates;
                       rawCoords = ring.map(pt => ({ lng: pt[0], lat: pt[1] }));
                   }
                   rawCoords.forEach(pt => {
                       const utm = proj4('EPSG:4326', 'EPSG:32717', [pt.lng, pt.lat]);
                       coordsText += `${utm[0].toFixed(2)} ${utm[1].toFixed(2)}\\n`;
                   });
                   
                   setTempPredioFormData({ 
                       geometry: feature, 
                       latlng: selectionContextMenu.latlng, 
                       geom_text: coordsText, 
                       geom_geojson: coordsText,
                       es_utm: true 
                   });
                   setIsAddingPredio(true);
                   setSelectionContextMenu(null);
                 }
               }} 
               style={{ width: '100%', padding: '8px 12px', textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '13px', color: '#0369a1', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '6px' }}
               onMouseOver={(e) => e.target.style.background = '#e0f2fe'}
               onMouseOut={(e) => e.target.style.background = 'transparent'}
            >
              💾 Guardar en BD (Predio)
            </button>
          </div>
        )}'''

if target_menu_pattern in gp_content:
    gp_content = gp_content.replace(target_menu_pattern, replacement_menu)
    with open(geoportal_path, 'w', encoding='utf-8') as f:
        f.write(gp_content)
    print("Updated Geoportal.jsx context menu successfully.")
else:
    print("Could not find selectionContextMenu in Geoportal.jsx")
