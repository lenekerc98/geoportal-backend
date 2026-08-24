import os

css_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\MapViewer\ShapefileAtlasModal.css'
jsx_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\MapViewer\ShapefileAtlasModal.jsx'
geoportal_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Geoportal\Geoportal.jsx'

# 1. ShapefileAtlasModal.css
css_content = '''/* Modal Overlay */
.atlas-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(8px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px;
}

/* Main Container */
.atlas-modal-container {
  background: var(--bg-panel, #ffffff);
  color: var(--text-main, #1e293b);
  border-radius: 16px;
  width: 95vw;
  max-width: 1300px;
  height: 92vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
  border: 1px solid var(--card-border, #e2e8f0);
  overflow: hidden;
  animation: atlasModalFadeIn 0.25s ease-out;
}

@keyframes atlasModalFadeIn {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}

/* Header */
.atlas-header {
  padding: 14px 20px;
  border-bottom: 1px solid var(--card-border, #e2e8f0);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-main, #f8fafc);
}

.atlas-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.atlas-title-group h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--accent-color, #0284c7);
  display: flex;
  align-items: center;
  gap: 8px;
}

.atlas-badge {
  font-size: 0.75rem;
  padding: 3px 8px;
  border-radius: 999px;
  font-weight: 600;
}

.atlas-badge-draft {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
}

.atlas-badge-saved {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.atlas-badge-converted {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
}

/* Navigation Toolbar */
.atlas-nav-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--card-bg, #ffffff);
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid var(--card-border, #e2e8f0);
}

.atlas-nav-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 6px 8px;
  color: var(--text-main, #334155);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.atlas-nav-btn:hover:not(:disabled) {
  background: var(--sidebar-hover, #f1f5f9);
  border-color: var(--card-border, #cbd5e1);
}

.atlas-nav-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.atlas-nav-status {
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0 8px;
  color: var(--text-main, #1e293b);
  white-space: nowrap;
}

/* Body Split Layout */
.atlas-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.atlas-map-pane {
  flex: 1.15;
  position: relative;
  border-right: 1px solid var(--card-border, #e2e8f0);
  background: #0f172a;
}

.atlas-form-pane {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  background: var(--bg-panel, #ffffff);
}

/* Map Meta Overlay */
.atlas-map-overlay {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 1000;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  color: #fff;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  font-size: 0.8rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  display: flex;
  gap: 16px;
}

.atlas-map-overlay-item {
  display: flex;
  flex-direction: column;
}

.atlas-map-overlay-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  color: #94a3b8;
  font-weight: 700;
}

.atlas-map-overlay-val {
  font-weight: 700;
  color: #38bdf8;
}

/* Form Styles */
.atlas-field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.atlas-field-group label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-muted, #64748b);
  display: flex;
  justify-content: space-between;
}

.atlas-row {
  display: flex;
  gap: 12px;
}

.atlas-row > * {
  flex: 1;
}

.atlas-input {
  background: var(--bg-main, #f8fafc);
  color: var(--text-main, #1e293b);
  border: 1px solid var(--card-border, #cbd5e1);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.88rem;
  outline: none;
  transition: border-color 0.15s ease;
  width: 100%;
  box-sizing: border-box;
}

.atlas-input:focus {
  border-color: var(--accent-color, #0284c7);
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.2);
}

/* Table Linderos */
.atlas-table-container {
  border: 1px solid var(--card-border, #e2e8f0);
  border-radius: 8px;
  overflow: hidden;
  max-height: 220px;
  overflow-y: auto;
}

.atlas-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
  text-align: left;
}

.atlas-table th {
  background: var(--bg-main, #f1f5f9);
  color: var(--text-muted, #475569);
  padding: 8px 10px;
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid var(--card-border, #e2e8f0);
}

.atlas-table td {
  padding: 6px 10px;
  border-bottom: 1px solid var(--card-border, #f1f5f9);
}

.atlas-table input {
  width: 100%;
  padding: 4px 6px;
  font-size: 0.78rem;
  border-radius: 4px;
  border: 1px solid var(--card-border, #cbd5e1);
  background: var(--bg-main, #fff);
  color: var(--text-main, #1e293b);
  box-sizing: border-box;
}

/* Footer Actions */
.atlas-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--card-border, #e2e8f0);
  background: var(--bg-main, #f8fafc);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.atlas-actions-right {
  display: flex;
  gap: 10px;
}

.atlas-btn-save {
  background: var(--accent-color, #0284c7);
  color: #fff;
  border: none;
  padding: 9px 18px;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.atlas-btn-save:hover:not(:disabled) {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.atlas-btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.atlas-btn-batch {
  background: #10b981;
  color: #fff;
  border: none;
  padding: 9px 18px;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.atlas-btn-batch:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
}

.atlas-btn-close {
  background: transparent;
  color: var(--text-muted, #64748b);
  border: 1px solid var(--card-border, #cbd5e1);
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.atlas-btn-close:hover {
  background: var(--sidebar-hover, #f1f5f9);
  color: var(--text-main, #1e293b);
}
'''

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(css_content)
print("Created ShapefileAtlasModal.css successfully.")

# 2. ShapefileAtlasModal.jsx
jsx_content = '''import React, { useState, useEffect, useMemo, useRef, useContext } from 'react';
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
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 19 });
    }
  }, [coords, map]);
  return null;
}

export default function ShapefileAtlasModal({ 
  geoJsonData, 
  onClose, 
  onSavedPredio, 
  fileName = "Shapefile" 
}) {
  const { activeEmpresa, activeProyecto, user } = useContext(AppContext);
  const token = localStorage.getItem('catastro_token');

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
          // Cerrar si está abierto
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
        // ring coords son [lng, lat]
        // Convertir a lat/lng para Leaflet y X/Y UTM para topología
        const latLngs = ring.map(pt => [pt[1], pt[0]]);
        const utmCoords = ring.map(pt => {
          const u = proj4('EPSG:4326', 'EPSG:32717', [pt[0], pt[1]]);
          return [u[0], u[1]];
        });

        // Calcular Área y Perímetro
        let area = 0;
        let perimetro = 0;
        const n = utmCoords.length - 1; // Último es igual al primero
        for (let i = 0; i < n; i++) {
          const x1 = utmCoords[i][0];
          const y1 = utmCoords[i][1];
          const x2 = utmCoords[i + 1][0];
          const y2 = utmCoords[i + 1][1];
          area += (x1 * y2) - (x2 * y1);
          perimetro += Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        }
        const areaM2 = Math.abs(area) / 2.0;
        const areaHa = areaM2 / 10000.0;

        results.push({
          id: `atlas_${idx}_${ringIdx}`,
          originalIndex: idx + 1,
          latLngs,
          utmCoords,
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
      // Extraer datos originales si existen en el Shapefile
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

      // Linderos y rumbos calculados
      const linderos = [];
      const n = feat.utmCoords.length - 1;
      for (let i = 0; i < n; i++) {
        const x1 = feat.utmCoords[i][0];
        const y1 = feat.utmCoords[i][1];
        const x2 = feat.utmCoords[i + 1][0];
        const y2 = feat.utmCoords[i + 1][1];
        const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2).toFixed(2);
        
        // Rumbo
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
        status: 'draft' // 'draft' | 'saved'
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

  // Buscar posesionario por cédula
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

  // Guardar Predio Actual en BD
  const handleSaveCurrent = async () => {
    if (!currentFeature || !currentDraft) return;

    const cod = currentDraft.cod_catastral.replace(/\s/g, '');
    if (cod.length !== 19) {
      Swal.fire('Atención', 'La Clave Catastral debe tener exactamente 19 dígitos.', 'warning');
      return;
    }

    setIsSaving(true);
    try {
      // 1. Validar / Crear Posesionario si no existe
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

      // 2. Preparar Coordenadas de Texto UTM para Predio
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
      
      // Actualizar estado a Guardado
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

      // Avanzar al siguiente si hay pendientes
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

  // Guardar Todos en Lote
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

            <MapContainer 
              center={currentFeature.latLngs[0]} 
              zoom={18} 
              style={{ width: '100%', height: '100%' }}
              zoomControl={false}
            >
              <TileLayer 
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" 
                maxZoom={20}
              />
              
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

              {/* Marcadores de vértices V1, V2... */}
              {currentFeature.latLngs.slice(0, -1).map((pt, vIdx) => (
                <CircleMarker 
                  key={`v-${vIdx}`} 
                  center={pt} 
                  radius={6} 
                  pathOptions={{
                    color: '#0284c7',
                    fillColor: '#ffffff',
                    fillOpacity: 1,
                    weight: 2
                  }} 
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
    f.write(jsx_content)
print("Created ShapefileAtlasModal.jsx successfully.")

# 3. Patch Geoportal.jsx
with open(geoportal_path, 'r', encoding='utf-8') as f:
    gp_content = f.read()

# Add import if not present
if 'import ShapefileAtlasModal from' not in gp_content:
    import_stmt = "import ShapefileAtlasModal from '../../components/MapViewer/ShapefileAtlasModal';\n"
    gp_content = import_stmt + gp_content
    print("Added ShapefileAtlasModal import.")

# Add atlas modal state
state_target = "  const [importedShapes, setImportedShapes] = useState(null);"
state_replacement = """  const [importedShapes, setImportedShapes] = useState(null);
  const [showAtlasModal, setShowAtlasModal] = useState(false);
  const [atlasFileName, setAtlasFileName] = useState('');"""

if state_target in gp_content and 'const [showAtlasModal, setShowAtlasModal]' not in gp_content:
    gp_content = gp_content.replace(state_target, state_replacement, 1)
    print("Added showAtlasModal state.")

# Update handleImportShapefile
old_import_code = """    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const buffer = evt.target.result;
        const geojson = await shp(buffer);
        setImportedShapes(geojson);
        setToastMsg({ type: 'success', title: 'Importado', message: 'Shapefile cargado al mapa visualmente.' });

        if (map && geojson.features && geojson.features.length > 0) {
          const group = L.geoJSON(geojson);
          map.fitBounds(group.getBounds());
        }
      } catch (err) {
        console.error(err);
        setToastMsg({ type: 'error', title: 'Error', message: 'Error leyendo Shapefile ZIP.' });
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = null;"""

new_import_code = """    const file = e.target.files[0];
    if (!file) return;
    setAtlasFileName(file.name);
    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const buffer = evt.target.result;
        const geojson = await shp(buffer);
        setImportedShapes(geojson);
        setShowAtlasModal(true);
        setToastMsg({ type: 'success', title: 'Atlas de Importación', message: 'Shapefile cargado en modo Atlas interactivo.' });

        if (map && geojson.features && geojson.features.length > 0) {
          const group = L.geoJSON(geojson);
          map.fitBounds(group.getBounds());
        }
      } catch (err) {
        console.error(err);
        setToastMsg({ type: 'error', title: 'Error', message: 'Error leyendo Shapefile ZIP.' });
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = null;"""

if old_import_code in gp_content:
    gp_content = gp_content.replace(old_import_code, new_import_code, 1)
    print("Updated handleImportShapefile to open Atlas.")

# Render ShapefileAtlasModal before closing tags in Geoportal.jsx
modal_render = """      {showAtlasModal && importedShapes && (
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
      )}
"""

if 'showAtlasModal && importedShapes' not in gp_content and '{/* Modal Carga Shapefile Dinámico */}' in gp_content:
    gp_content = gp_content.replace('{/* Modal Carga Shapefile Dinámico */}', modal_render + '\n      {/* Modal Carga Shapefile Dinámico */}', 1)
    print("Rendered ShapefileAtlasModal in Geoportal.jsx.")

with open(geoportal_path, 'w', encoding='utf-8') as f:
    f.write(gp_content)
print("Updated Geoportal.jsx successfully.")
