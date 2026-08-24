import os

css_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\MapViewer\ShapefileAtlasModal.css'
jsx_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\MapViewer\ShapefileAtlasModal.jsx'

# 1. Update CSS
with open(css_path, 'r', encoding='utf-8') as f:
    css = f.read()

layer_css = '''
/* Map Layer Selector */
.atlas-map-layer-selector {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1000;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  padding: 4px;
  border-radius: 8px;
  display: flex;
  gap: 4px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.atlas-layer-btn {
  background: transparent;
  color: #94a3b8;
  border: none;
  padding: 4px 8px;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.atlas-layer-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.1);
}

.atlas-layer-btn.active {
  background: var(--accent-color, #0284c7);
  color: #ffffff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}
'''

if '.atlas-map-layer-selector' not in css:
    css += layer_css
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write(css)
    print("Updated ShapefileAtlasModal.css with layer selector styles.")

# 2. Update JSX
new_jsx = '''import React, { useState, useEffect, useMemo, useRef, useContext } from 'react';
import { 
  X, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, 
  Save, CheckCircle2, AlertCircle, Loader2, Sparkles, Database,
  Layers, MapPin, Compass
} from 'lucide-react';
import { MapContainer, TileLayer, Polygon, CircleMarker, Marker, useMap } from 'react-leaflet';
import L from 'leaflet';
import proj4 from 'proj4';
import Swal from 'sweetalert2';
import { API_URL } from '../../services/api';
import { AppContext } from '../../context/AppContext';
import './ShapefileAtlasModal.css';

proj4.defs("EPSG:32717", "+proj=utm +zone=17 +south +datum=WGS84 +units=m +no_defs");

function MapBoundsUpdater({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords && coords.length > 0) {
      const bounds = L.latLngBounds(coords);
      map.fitBounds(bounds, { padding: [45, 45], maxZoom: 19 });
    }
  }, [coords, map]);
  return null;
}

// Helper: Crear icono del vértice con su número (V1, V2, ...)
const createVertexLabelIcon = (num, ptLat, ptLng, centerLat, centerLng) => {
  const dy = ptLat - centerLat;
  const dx = ptLng - centerLng;
  const angle = Math.atan2(dy, dx);
  const dist = 16;
  const offX = Math.cos(angle) * dist;
  const offY = -Math.sin(angle) * dist; // Leaflet coord Y está invertido

  return L.divIcon({
    className: 'atlas-vertex-marker-node',
    html: `
      <div style="position: relative; width: 14px; height: 14px; background: #0284c7; border: 2.5px solid #ffffff; border-radius: 50%; box-shadow: 0 2px 5px rgba(0,0,0,0.6);">
        <span style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%) translate(${offX.toFixed(1)}px, ${offY.toFixed(1)}px); font-size: 11px; font-weight: 800; color: #ffffff; background: #0f172a; border: 1.5px solid #38bdf8; padding: 1px 6px; border-radius: 5px; white-space: nowrap; box-shadow: 0 2px 6px rgba(0,0,0,0.5); pointer-events: none;">
          V${num}
        </span>
      </div>
    `,
    iconSize: [14, 14],
    iconAnchor: [7, 7]
  });
};

// Helper: Crear cota de distancia en el medio de cada tramo
const createDistanceLabelIcon = (medida) => {
  return L.divIcon({
    className: 'atlas-dist-badge',
    html: `
      <div style="font-size: 10px; font-weight: 700; color: #0f172a; background: rgba(255, 255, 255, 0.95); border: 1px solid #94a3b8; padding: 1px 5px; border-radius: 4px; white-space: nowrap; transform: translate(-50%, -50%); box-shadow: 0 1px 4px rgba(0,0,0,0.3); pointer-events: none;">
        ${medida} m
      </div>
    `,
    iconSize: [0, 0],
    iconAnchor: [0, 0]
  });
};

export default function ShapefileAtlasModal({ 
  geoJsonData, 
  onClose, 
  onSavedPredio, 
  fileName = "Shapefile" 
}) {
  const { activeEmpresa, activeProyecto, user } = useContext(AppContext);
  const token = localStorage.getItem('catastro_token');

  const [baseMap, setBaseMap] = useState('google-sat'); // 'google-sat' | 'osm' | 'hybrid' | 'esri'

  // 1. Extraer y Normalizar Polígonos y Polilíneas
  const normalizedFeatures = useMemo(() => {
    if (!geoJsonData || !geoJsonData.features) return [];
    
    const results = [];
    geoJsonData.features.forEach((feat, idx) => {
      if (!feat || !feat.geometry) return;
      const geom = feat.geometry;
      let rawRings = [];
      let wasConverted = false;

      if (geom.type === 'Polygon') {
        rawRings = [geom.coordinates[0]];
      } else if (geom.type === 'MultiPolygon') {
        geom.coordinates.forEach(poly => {
          if (poly && poly[0]) rawRings.push(poly[0]);
        });
      } else if (geom.type === 'LineString') {
        if (geom.coordinates && geom.coordinates.length >= 3) {
          const c = [...geom.coordinates];
          if (c[0][0] !== c[c.length - 1][0] || c[0][1] !== c[c.length - 1][1]) {
            c.push([...c[0]]);
          }
          rawRings = [c];
          wasConverted = true;
        }
      } else if (geom.type === 'MultiLineString') {
        geom.coordinates.forEach(line => {
          if (line && line.length >= 3) {
            const c = [...line];
            if (c[0][0] !== c[c.length - 1][0] || c[0][1] !== c[c.length - 1][1]) {
              c.push([...c[0]]);
            }
            rawRings.push(c);
            wasConverted = true;
          }
        });
      }

      rawRings.forEach((ring, ringIdx) => {
        const latLngs = ring.map(pt => [pt[1], pt[0]]);
        const utmCoords = ring.map(pt => {
          const u = proj4('EPSG:4326', 'EPSG:32717', [pt[0], pt[1]]);
          return [u[0], u[1]];
        });

        // Calcular Centroide para posicionar etiquetas hacia afuera
        let latSum = 0;
        let lngSum = 0;
        const nPoints = latLngs.length - 1;
        for (let i = 0; i < nPoints; i++) {
          latSum += latLngs[i][0];
          lngSum += latLngs[i][1];
        }
        const centerLat = latSum / (nPoints || 1);
        const centerLng = lngSum / (nPoints || 1);

        // Calcular Área y Perímetro
        let area = 0;
        let perimetro = 0;
        const midPoints = [];

        for (let i = 0; i < nPoints; i++) {
          const x1 = utmCoords[i][0];
          const y1 = utmCoords[i][1];
          const x2 = utmCoords[i + 1][0];
          const y2 = utmCoords[i + 1][1];
          area += (x1 * y2) - (x2 * y1);
          const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
          perimetro += dist;

          // Punto medio en Lat/Lng para la cota de distancia
          const midLat = (latLngs[i][0] + latLngs[i + 1][0]) / 2;
          const midLng = (latLngs[i][1] + latLngs[i + 1][1]) / 2;
          midPoints.push({
            center: [midLat, midLng],
            distancia: dist.toFixed(2)
          });
        }
        const areaM2 = Math.abs(area) / 2.0;
        const areaHa = areaM2 / 10000.0;

        results.push({
          id: `atlas_${idx}_${ringIdx}`,
          originalIndex: idx + 1,
          latLngs,
          utmCoords,
          centerLat,
          centerLng,
          midPoints,
          areaM2: areaM2.toFixed(2),
          areaHa: areaHa.toFixed(4),
          perimetro: perimetro.toFixed(2),
          wasConverted,
          originalProperties: feat.properties || {}
        });
      });
    });

    return results;
  }, [geoJsonData]);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [drafts, setDrafts] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [isBatchSaving, setIsBatchSaving] = useState(false);

  // Inicializar borradores
  useEffect(() => {
    const initial = {};
    normalizedFeatures.forEach((feat, idx) => {
      const props = feat.originalProperties;
      let initCedula = '';
      let initNombre = '';
      let initClave = '';

      Object.keys(props).forEach(k => {
        const val = String(props[k] || '');
        const upper = k.toUpperCase();
        if (upper.includes('CEDULA') || upper.includes('RUC') || upper.includes('IDENTIFIC')) initCedula = val;
        if (upper.includes('NOMBRE') || upper.includes('PROPIETARIO') || upper.includes('POSESION')) initNombre = val;
        if (upper.includes('CLAVE') || upper.includes('CATAST') || upper.includes('CODIGO')) initClave = val;
      });

      const linderos = [];
      const n = feat.utmCoords.length - 1;
      for (let i = 0; i < n; i++) {
        const x1 = feat.utmCoords[i][0];
        const y1 = feat.utmCoords[i][1];
        const x2 = feat.utmCoords[i + 1][0];
        const y2 = feat.utmCoords[i + 1][1];
        const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2).toFixed(2);
        
        const dx = x2 - x1;
        const dy = y2 - y1;
        let rumbo = '-';
        if (dx !== 0 || dy !== 0) {
          const ang = Math.atan2(Math.abs(dx), Math.abs(dy)) * (180 / Math.PI);
          const g = Math.floor(ang);
          const m = Math.floor((ang - g) * 60);
          const s = ((ang - g - m / 60) * 3600).toFixed(1);
          const ns = dy >= 0 ? 'N' : 'S';
          const ew = dx >= 0 ? 'E' : 'W';
          rumbo = `${ns} ${g}°${m}'${s}" ${ew}`;
        }

        linderos.push({
          tramo: `V${i + 1} - V${i + 2}`,
          distancia: dist,
          rumbo,
          colindante: ''
        });
      }

      initial[idx] = {
        cod_catastral: initClave || '',
        cedula: initCedula || '',
        nombre_posesionario: initNombre || '',
        posesionario_id: null,
        linderos,
        status: 'draft'
      };
    });
    setDrafts(initial);
  }, [normalizedFeatures]);

  const currentFeature = normalizedFeatures[currentIndex];
  const currentDraft = drafts[currentIndex] || {
    cod_catastral: '',
    cedula: '',
    nombre_posesionario: '',
    posesionario_id: null,
    linderos: [],
    status: 'draft'
  };

  const handleUpdateDraft = (field, value) => {
    setDrafts(prev => ({
      ...prev,
      [currentIndex]: {
        ...prev[currentIndex],
        [field]: value
      }
    }));
  };

  const handleUpdateLindero = (linderoIdx, colindante) => {
    setDrafts(prev => {
      const cur = prev[currentIndex] || {};
      const newLinderos = [...(cur.linderos || [])];
      if (newLinderos[linderoIdx]) {
        newLinderos[linderoIdx] = { ...newLinderos[linderoIdx], colindante };
      }
      return {
        ...prev,
        [currentIndex]: {
          ...cur,
          linderos: newLinderos
        }
      };
    });
  };

  const handleBuscarPosesionario = async (cedulaVal) => {
    if (!cedulaVal || cedulaVal.length < 10) return;
    try {
      const res = await fetch(`${API_URL}/api/gis/posesionarios/buscar/${cedulaVal}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const posData = await res.json();
        handleUpdateDraft('nombre_posesionario', posData.nombre || '');
        handleUpdateDraft('posesionario_id', posData.id || null);
      }
    } catch (e) {
      console.error("Error buscando posesionario:", e);
    }
  };

  const handleSaveCurrent = async () => {
    if (!currentFeature || !currentDraft) return;

    const cod = currentDraft.cod_catastral.replace(/\s/g, '');
    if (cod.length !== 19) {
      Swal.fire('Atención', 'La Clave Catastral debe tener exactamente 19 dígitos.', 'warning');
      return;
    }

    setIsSaving(true);
    try {
      let finalPosId = currentDraft.posesionario_id;
      if (!finalPosId && currentDraft.cedula && currentDraft.nombre_posesionario) {
        const posRes = await fetch(`${API_URL}/api/gis/posesionarios`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ cedula: currentDraft.cedula, nombre: currentDraft.nombre_posesionario })
        });
        if (posRes.ok) {
          const posJson = await posRes.json();
          finalPosId = posJson.id;
        }
      }

      let coordsText = '';
      currentFeature.utmCoords.forEach(pt => {
        coordsText += `${pt[0].toFixed(2)} ${pt[1].toFixed(2)}\\n`;
      });

      const colindantesList = (currentDraft.linderos || []).map(l => l.colindante || '');
      const rumbosList = (currentDraft.linderos || []).map(l => l.rumbo || '');

      const payload = {
        cod_catastral: cod,
        posesionario_id: finalPosId || null,
        cedula_temporal: (!finalPosId && currentDraft.cedula) ? currentDraft.cedula : undefined,
        nombre_temporal: (!finalPosId && currentDraft.nombre_posesionario) ? currentDraft.nombre_posesionario : undefined,
        empresa_id: activeEmpresa?.id || null,
        proyecto_id: activeProyecto?.id || null,
        geom_geojson: {
          type: "Polygon",
          coordinates: [currentFeature.utmCoords]
        },
        geom_text: coordsText,
        colindantes: colindantesList,
        rumbos: rumbosList,
        es_utm: true
      };

      const res = await fetch(`${API_URL}/api/gis/predios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Error al guardar el predio en la base de datos');
      }

      const savedData = await res.json();
      
      setDrafts(prev => ({
        ...prev,
        [currentIndex]: {
          ...prev[currentIndex],
          status: 'saved',
          savedPredioId: savedData.id
        }
      }));

      Swal.fire({
        title: '¡Guardado!',
        text: `Predio con Clave ${cod} registrado exitosamente en la BD.`,
        icon: 'success',
        timer: 1800,
        showConfirmButton: false
      });

      if (onSavedPredio) onSavedPredio(savedData);

      if (currentIndex < normalizedFeatures.length - 1) {
        setCurrentIndex(currentIndex + 1);
      }
    } catch (err) {
      console.error(err);
      Swal.fire('Error', err.message, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAll = async () => {
    const readyIndices = Object.keys(drafts).filter(k => {
      const d = drafts[k];
      return d && d.status !== 'saved' && d.cod_catastral.replace(/\s/g, '').length === 19;
    });

    if (readyIndices.length === 0) {
      Swal.fire('Sin elementos listos', 'Completa la clave catastral de 19 dígitos en los polígonos que desees registrar.', 'info');
      return;
    }

    const confirm = await Swal.fire({
      title: `¿Guardar ${readyIndices.length} predios?`,
      text: 'Se insertarán en la base de datos catastral generando sus vértices y linderos.',
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Sí, registrar en BD',
      cancelButtonText: 'Cancelar'
    });

    if (!confirm.isConfirmed) return;

    setIsBatchSaving(true);
    let successCount = 0;

    for (const idxStr of readyIndices) {
      const idx = parseInt(idxStr);
      const feat = normalizedFeatures[idx];
      const draft = drafts[idx];
      if (!feat || !draft) continue;

      try {
        let finalPosId = draft.posesionario_id;
        if (!finalPosId && draft.cedula && draft.nombre_posesionario) {
          const posRes = await fetch(`${API_URL}/api/gis/posesionarios`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ cedula: draft.cedula, nombre: draft.nombre_posesionario })
          });
          if (posRes.ok) {
            const posJson = await posRes.json();
            finalPosId = posJson.id;
          }
        }

        let coordsText = '';
        feat.utmCoords.forEach(pt => {
          coordsText += `${pt[0].toFixed(2)} ${pt[1].toFixed(2)}\\n`;
        });

        const payload = {
          cod_catastral: draft.cod_catastral.replace(/\s/g, ''),
          posesionario_id: finalPosId || null,
          cedula_temporal: (!finalPosId && draft.cedula) ? draft.cedula : undefined,
          nombre_temporal: (!finalPosId && draft.nombre_posesionario) ? draft.nombre_posesionario : undefined,
          empresa_id: activeEmpresa?.id || null,
          proyecto_id: activeProyecto?.id || null,
          geom_geojson: { type: "Polygon", coordinates: [feat.utmCoords] },
          geom_text: coordsText,
          colindantes: (draft.linderos || []).map(l => l.colindante || ''),
          rumbos: (draft.linderos || []).map(l => l.rumbo || ''),
          es_utm: true
        };

        const res = await fetch(`${API_URL}/api/gis/predios`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          successCount++;
          setDrafts(prev => ({
            ...prev,
            [idx]: { ...prev[idx], status: 'saved' }
          }));
        }
      } catch (e) {
        console.error(`Error en predio ${idx}:`, e);
      }
    }

    setIsBatchSaving(false);
    Swal.fire('Proceso Completado', `Se guardaron ${successCount} de ${readyIndices.length} predios en la base de datos.`, 'success');
    if (onSavedPredio) onSavedPredio();
  };

  const totalPolygons = normalizedFeatures.length;
  const savedCount = Object.values(drafts).filter(d => d.status === 'saved').length;

  if (totalPolygons === 0) {
    return (
      <div className="atlas-modal-overlay">
        <div className="atlas-modal-container" style={{ maxHeight: '250px', textAlign: 'center', padding: '30px' }}>
          <h3>No se detectaron polígonos válidos en el archivo</h3>
          <p style={{ color: 'var(--text-muted)' }}>Asegúrate de que el Shapefile contenga polígonos o polilíneas de al menos 3 vértices.</p>
          <button className="atlas-btn-close" style={{ marginTop: '20px' }} onClick={onClose}>Cerrar</button>
        </div>
      </div>
    );
  }

  return (
    <div className="atlas-modal-overlay">
      <div className="atlas-modal-container">
        
        {/* Header */}
        <div className="atlas-header">
          <div className="atlas-title-group">
            <h2>
              <Sparkles size={20} /> Asistente Atlas de Importación
            </h2>
            <span className="atlas-badge atlas-badge-draft">
              📁 {fileName}
            </span>
            {currentFeature?.wasConverted && (
              <span className="atlas-badge atlas-badge-converted">
                📐 Polilínea cerrada a Polígono
              </span>
            )}
            {currentDraft.status === 'saved' ? (
              <span className="atlas-badge atlas-badge-saved">
                ✓ Registrado en BD
              </span>
            ) : (
              <span className="atlas-badge atlas-badge-draft">
                🟡 Borrador en memoria
              </span>
            )}
          </div>

          {/* Navigation Controls */}
          <div className="atlas-nav-toolbar">
            <button 
              className="atlas-nav-btn" 
              onClick={() => setCurrentIndex(0)} 
              disabled={currentIndex === 0}
              title="Primer polígono"
            >
              <ChevronsLeft size={18} />
            </button>
            <button 
              className="atlas-nav-btn" 
              onClick={() => setCurrentIndex(prev => Math.max(0, prev - 1))} 
              disabled={currentIndex === 0}
              title="Anterior"
            >
              <ChevronLeft size={18} />
            </button>

            <span className="atlas-nav-status">
              Hoja {currentIndex + 1} de {totalPolygons}
            </span>

            <button 
              className="atlas-nav-btn" 
              onClick={() => setCurrentIndex(prev => Math.min(totalPolygons - 1, prev + 1))} 
              disabled={currentIndex === totalPolygons - 1}
              title="Siguiente"
            >
              <ChevronRight size={18} />
            </button>
            <button 
              className="atlas-nav-btn" 
              onClick={() => setCurrentIndex(totalPolygons - 1)} 
              disabled={currentIndex === totalPolygons - 1}
              title="Último polígono"
            >
              <ChevronsRight size={18} />
            </button>
          </div>

          <button className="atlas-nav-btn" onClick={onClose} title="Cerrar Atlas">
            <X size={20} />
          </button>
        </div>

        {/* Body Split */}
        <div className="atlas-body">
          
          {/* Left: Mini-Map Viewer */}
          <div className="atlas-map-pane">
            <div className="atlas-map-overlay">
              <div className="atlas-map-overlay-item">
                <span className="atlas-map-overlay-label">Área</span>
                <span className="atlas-map-overlay-val">{currentFeature.areaM2} m² ({currentFeature.areaHa} Ha)</span>
              </div>
              <div className="atlas-map-overlay-item">
                <span className="atlas-map-overlay-label">Perímetro</span>
                <span className="atlas-map-overlay-val">{currentFeature.perimetro} m</span>
              </div>
              <div className="atlas-map-overlay-item">
                <span className="atlas-map-overlay-label">Vértices</span>
                <span className="atlas-map-overlay-val">{currentFeature.latLngs.length - 1} pts</span>
              </div>
            </div>

            {/* Base Layer Switcher */}
            <div className="atlas-map-layer-selector">
              <button 
                className={`atlas-layer-btn ${baseMap === 'google-sat' ? 'active' : ''}`}
                onClick={() => setBaseMap('google-sat')}
                title="Google Satélite"
              >
                🛰️ Satélite
              </button>
              <button 
                className={`atlas-layer-btn ${baseMap === 'osm' ? 'active' : ''}`}
                onClick={() => setBaseMap('osm')}
                title="OpenStreetMap"
              >
                🗺️ OpenStreetMap
              </button>
              <button 
                className={`atlas-layer-btn ${baseMap === 'hybrid' ? 'active' : ''}`}
                onClick={() => setBaseMap('hybrid')}
                title="Google Híbrido"
              >
                🏙️ Híbrido
              </button>
              <button 
                className={`atlas-layer-btn ${baseMap === 'esri' ? 'active' : ''}`}
                onClick={() => setBaseMap('esri')}
                title="Esri World Imagery"
              >
                🌍 Esri
              </button>
            </div>

            <MapContainer 
              center={currentFeature.latLngs[0]} 
              zoom={18} 
              style={{ width: '100%', height: '100%' }}
              zoomControl={false}
              maxZoom={25}
            >
              {/* Tile Layers with proper maxNativeZoom */}
              {baseMap === 'google-sat' && (
                <TileLayer 
                  url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
                  attribution="Google Satélite"
                  maxNativeZoom={20}
                  maxZoom={25}
                />
              )}
              {baseMap === 'osm' && (
                <TileLayer 
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  maxNativeZoom={19}
                  maxZoom={25}
                />
              )}
              {baseMap === 'hybrid' && (
                <TileLayer 
                  url="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
                  attribution="Google Híbrido"
                  maxNativeZoom={20}
                  maxZoom={25}
                />
              )}
              {baseMap === 'esri' && (
                <TileLayer 
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                  attribution="Tiles &copy; Esri"
                  maxNativeZoom={18}
                  maxZoom={25}
                />
              )}
              
              <MapBoundsUpdater coords={currentFeature.latLngs} />

              <Polygon 
                positions={currentFeature.latLngs} 
                pathOptions={{
                  color: currentDraft.status === 'saved' ? '#22c55e' : '#0284c7',
                  fillColor: currentDraft.status === 'saved' ? '#22c55e' : '#38bdf8',
                  fillOpacity: 0.35,
                  weight: 3
                }} 
              />

              {/* Marcadores de vértices V1, V2... con etiquetas de texto visibles */}
              {currentFeature.latLngs.slice(0, -1).map((pt, vIdx) => (
                <Marker
                  key={`v-${vIdx}`}
                  position={pt}
                  icon={createVertexLabelIcon(
                    vIdx + 1, 
                    pt[0], 
                    pt[1], 
                    currentFeature.centerLat, 
                    currentFeature.centerLng
                  )}
                />
              ))}

              {/* Cotas de distancia en cada tramo del polígono */}
              {currentFeature.midPoints.map((mp, mIdx) => (
                <Marker 
                  key={`dist-${mIdx}`}
                  position={mp.center}
                  icon={createDistanceLabelIcon(mp.distancia)}
                />
              ))}
            </MapContainer>
          </div>

          {/* Right: Attribute Form & Topology Table */}
          <div className="atlas-form-pane">
            
            {/* Clave Catastral */}
            <div className="atlas-field-group">
              <label>
                <span>Clave Catastral (19 dígitos) *</span>
                <span style={{ fontSize: '0.75rem', fontWeight: 'normal' }}>Prov-Cant-Parr-Zona-Sect-Pol-Pred-Div</span>
              </label>
              <input 
                type="text" 
                className="atlas-input"
                value={currentDraft.cod_catastral}
                onChange={e => handleUpdateDraft('cod_catastral', e.target.value)}
                placeholder="Ej. 1211500101001000100"
                maxLength={19}
              />
            </div>

            {/* Posesionario */}
            <div className="atlas-row">
              <div className="atlas-field-group">
                <label>Cédula / RUC</label>
                <input 
                  type="text" 
                  className="atlas-input"
                  value={currentDraft.cedula}
                  onChange={e => {
                    handleUpdateDraft('cedula', e.target.value);
                    if (e.target.value.length >= 10) handleBuscarPosesionario(e.target.value);
                  }}
                  placeholder="10 dígitos..."
                  maxLength={13}
                />
              </div>
              <div className="atlas-field-group" style={{ flex: 1.5 }}>
                <label>Nombre del Posesionario</label>
                <input 
                  type="text" 
                  className="atlas-input"
                  value={currentDraft.nombre_posesionario}
                  onChange={e => handleUpdateDraft('nombre_posesionario', e.target.value)}
                  placeholder="Nombre completo..."
                />
              </div>
            </div>

            {/* Tabla de Linderos & Colindantes */}
            <div className="atlas-field-group" style={{ flex: 1 }}>
              <label>
                <span>Linderos y Colindancias</span>
                <span style={{ fontSize: '0.75rem' }}>{currentDraft.linderos.length} tramos calculados</span>
              </label>

              <div className="atlas-table-container">
                <table className="atlas-table">
                  <thead>
                    <tr>
                      <th style={{ width: '75px' }}>Tramo</th>
                      <th style={{ width: '80px' }}>Distancia</th>
                      <th style={{ width: '130px' }}>Rumbo</th>
                      <th>Colindante</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentDraft.linderos.map((lin, lIdx) => (
                      <tr key={`lin-${lIdx}`}>
                        <td style={{ fontWeight: '600', color: 'var(--accent-color)' }}>{lin.tramo}</td>
                        <td>{lin.distancia} m</td>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{lin.rumbo}</td>
                        <td>
                          <input 
                            type="text" 
                            value={lin.colindante || ''}
                            onChange={e => handleUpdateLindero(lIdx, e.target.value)}
                            placeholder="Ej. Calle Principal / Pedro Díaz"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

        </div>

        {/* Footer */}
        <div className="atlas-footer">
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '15px' }}>
            <span>Registrados: <b>{savedCount}</b> de {totalPolygons}</span>
            <span>Empresa: <b>{activeEmpresa?.nombre || 'General'}</b></span>
          </div>

          <div className="atlas-actions-right">
            <button className="atlas-btn-close" onClick={onClose}>
              Cerrar
            </button>

            <button 
              className="atlas-btn-save" 
              onClick={handleSaveCurrent}
              disabled={isSaving || currentDraft.status === 'saved'}
            >
              {isSaving ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
              {currentDraft.status === 'saved' ? 'Predio Registrado ✓' : 'Guardar este Predio en BD'}
            </button>

            {totalPolygons > 1 && (
              <button 
                className="atlas-btn-batch" 
                onClick={handleSaveAll}
                disabled={isBatchSaving}
              >
                {isBatchSaving ? <Loader2 className="spin" size={16} /> : <Database size={16} />}
                Guardar Todos en BD
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
'''

with open(jsx_path, 'w', encoding='utf-8') as f:
    f.write(new_jsx)
print("Updated ShapefileAtlasModal.jsx with OpenStreetMap, layer switcher, fixed zoom and V1..Vn vertex labels.")
