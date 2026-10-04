# -*- coding: utf-8 -*-
import os
import re
import json

base_dir = r"c:\LNCZ\proyecto-catastro-2026\movil"

print("--- 1. PATCHING DrawingToolbarMobile.jsx (Ultra-Clean Slim Header Pill) ---")
dt_path = os.path.join(base_dir, "src", "components", "DrawingToolbarMobile.jsx")
with open(dt_path, "r", encoding="utf-8") as f:
    dt_code = f.read()

# Replace manual drawing widget (lines ~573 to ~707) with slim top pill
old_dt_pattern = r"\{/\* Widget Flotante de Dibujo en Pantalla.*?\n\s*\{/\* Barra Inferior del Mapa"

new_dt_widget = """{/* Barra Flotante Superior de Dibujo: Ultra-Compacta, Moderna y Limpia (~42px) */}
      {isManualDrawing && (
        <div 
          className="drawing-top-pill"
          style={{
            position: 'fixed',
            top: '56px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 9999,
            width: 'calc(100% - 20px)',
            maxWidth: '420px',
            background: 'rgba(255, 255, 255, 0.96)',
            backdropFilter: 'blur(10px)',
            border: '1.5px solid #0284c7',
            borderRadius: '14px',
            boxShadow: '0 4px 18px rgba(0, 0, 0, 0.18)',
            padding: '5px 10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
            animation: 'fadeInDown 0.2s ease',
            userSelect: 'none'
          }}
        >
          {/* Métricas: Puntos y Área en 1 sola línea compacta */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
            <span style={{
              background: '#e0f2fe',
              color: '#0284c7',
              fontWeight: '900',
              fontSize: '11px',
              padding: '2px 7px',
              borderRadius: '6px',
              whiteSpace: 'nowrap'
            }}>
              ✏️ {manualVertices.length} pts
            </span>

            {currentManualArea > 0 && (
              <span style={{
                fontSize: '11.5px',
                fontWeight: '800',
                color: '#15803d',
                whiteSpace: 'nowrap',
                background: '#f0fdf4',
                padding: '2px 6px',
                borderRadius: '6px',
                border: '1px solid #bbf7d0'
              }}>
                {currentManualArea >= 10000 
                  ? `${(currentManualArea / 10000).toFixed(4)} ha` 
                  : `${currentManualArea.toLocaleString('es-EC', { maximumFractionDigits: 1 })} m²`}
              </span>
            )}
          </div>

          {/* Botones de acción directos */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexShrink: 0 }}>
            {manualVertices.length > 0 && (
              <button 
                type="button"
                onClick={handleUndoManualVertex}
                style={{
                  background: '#f8fafc',
                  color: '#475569',
                  border: '1px solid #cbd5e1',
                  borderRadius: '8px',
                  height: '30px',
                  padding: '0 7px',
                  fontSize: '10.5px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '3px'
                }}
                title="Deshacer último punto"
              >
                <Undo2 size={12} /> Deshacer
              </button>
            )}

            {manualVertices.length >= 3 && (
              <button 
                type="button"
                onClick={handleFinishManualDrawing}
                style={{
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  height: '30px',
                  padding: '0 9px',
                  fontSize: '11px',
                  fontWeight: '800',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  boxShadow: '0 2px 6px rgba(16, 185, 129, 0.4)'
                }}
                title="Finalizar polígono y pasar a la ficha"
              >
                <CheckSquare size={13} /> Finalizar
              </button>
            )}

            <button 
              type="button"
              onClick={handleCancelManualDrawing}
              style={{
                background: '#fff1f2',
                color: '#f43f5e',
                border: '1px solid #fecdd3',
                borderRadius: '8px',
                width: '30px',
                height: '30px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                flexShrink: 0
              }}
              title="Cancelar dibujo"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Barra Inferior del Mapa"""

dt_code = re.sub(old_dt_pattern, new_dt_widget, dt_code, flags=re.DOTALL)
with open(dt_path, "w", encoding="utf-8") as f:
    f.write(dt_code)
print("Saved clean DrawingToolbarMobile.jsx")


print("--- 2. PATCHING MapTab.jsx (Remove (+) circles, line tapping anywhere, slim bottom card) ---")
maptab_path = os.path.join(base_dir, "src", "pages", "MapTab", "MapTab.jsx")
with open(maptab_path, "r", encoding="utf-8") as f:
    maptab_code = f.read()

# 2a. Update createSegmentMeasureIcon to be clean and clickable
old_measure_icon_pattern = r"// Helper: Icono para medidas métricas en vivo.*?const createSegmentMeasureIcon = \(distMeters, angle = 0, strokeColor = '#8b5cf6'\) => \{.*?\}\;\n\n"
new_measure_icon = """// Helper: Icono para medidas métricas en vivo en cada línea del polígono (Limpio y Clickable)
const createSegmentMeasureIcon = (distMeters, angle = 0, strokeColor = '#8b5cf6') => {
  const safeText = distMeters < 1000 
    ? `${distMeters.toFixed(1)} m` 
    : `${(distMeters / 1000).toFixed(2)} km`;
  return L.divIcon({
    className: 'segment-measure-badge',
    html: `
      <div style="
        position: absolute;
        transform: translate(-50%, -50%) rotate(${angle}deg);
        background: rgba(255, 255, 255, 0.94);
        color: #1e293b;
        border: 1.5px solid ${strokeColor};
        border-radius: 999px;
        padding: 2px 7px;
        font-size: 9.5px;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        white-space: nowrap;
        box-shadow: 0 1px 4px rgba(0,0,0,0.25);
        cursor: pointer;
        pointer-events: auto;
      " title="Medida del tramo. Toca para insertar punto en esta línea">
        ${safeText}
      </div>
    `,
    iconSize: [0, 0],
    iconAnchor: [0, 0]
  });
};

"""
maptab_code = re.sub(old_measure_icon_pattern, new_measure_icon, maptab_code, flags=re.DOTALL)
print("Updated createSegmentMeasureIcon")

# 2b. Update renderSegmentMeasures to accept onSegmentClick
old_render_measures_pattern = r"// Renderizar medidas por cada línea cuando haya 2 o más puntos\s+const renderSegmentMeasures = \(verts, isClosed = true, color = '#8b5cf6', keyPrefix = 'seg'\) => \{.*?return segments;\s*\};"
new_render_measures = """// Renderizar medidas por cada línea cuando haya 2 o más puntos
const renderSegmentMeasures = (verts, isClosed = true, color = '#8b5cf6', keyPrefix = 'seg', onSegmentClick = null) => {
  if (!verts || verts.length < 2) return null;
  const count = isClosed && verts.length >= 3 ? verts.length : verts.length - 1;
  const segments = [];
  for (let i = 0; i < count; i++) {
    const nextIdx = (i + 1) % verts.length;
    const p1 = verts[i];
    const p2 = verts[nextIdx];
    if (!p1 || !p2 || !isFinite(p1.lat) || !isFinite(p1.lng) || !isFinite(p2.lat) || !isFinite(p2.lng)) continue;
    let dist = 0;
    if (p1.x && p2.x && p1.y && p2.y) {
      dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
    } else {
      dist = L.latLng(p1.lat, p1.lng).distanceTo(L.latLng(p2.lat, p2.lng));
    }
    const midLat = (p1.lat + p2.lat) / 2;
    const midLng = (p1.lng + p2.lng) / 2;
    let angle = Math.atan2(-(p2.lat - p1.lat), (p2.lng - p1.lng)) * (180 / Math.PI);
    if (angle > 90 || angle < -90) angle += 180;

    const insertIdx = i + 1;
    const p1Label = `P${String(i + 1).padStart(2, '0')}`;
    const p2Label = `P${String(nextIdx + 1).padStart(2, '0')}`;
    const newLabel = `P${String(insertIdx + 1).padStart(2, '0')}`;

    segments.push(
      <Marker
        key={`${keyPrefix}-${i}`}
        position={[midLat, midLng]}
        icon={createSegmentMeasureIcon(dist, angle, color)}
        eventHandlers={{
          click: (e) => {
            L.DomEvent.stopPropagation(e);
            if (onSegmentClick) {
              onSegmentClick([midLat, midLng], insertIdx, p1Label, p2Label, newLabel);
            }
          }
        }}
      />
    );
  }
  return segments;
};"""

maptab_code = re.sub(old_render_measures_pattern, new_render_measures, maptab_code, flags=re.DOTALL)
print("Updated renderSegmentMeasures")

# 2c. In handleMapClick, increase detection to 48px and compute projected latlng
old_edge_click_pattern = r"// Si ya hay 2 o más vértices, verificar si el toque fue sobre o cerca de una línea entre dos puntos.*?if \(minPixelDist <= 35 && bestInsertIdx !== -1\) \{.*?handleInsertVertexAt\(latlng, bestInsertIdx, p1Label, p2Label, newLabel\);\s*return;\s*\}"

new_edge_click = """// Si ya hay 2 o más vértices, verificar si el toque fue sobre o cerca de CUALQUIER punto de la línea
    if (manualVertices.length >= 2 && mapInstance) {
      try {
        const ptClicked = mapInstance.latLngToLayerPoint(latlng);
        let minPixelDist = Infinity;
        let bestInsertIdx = -1;
        let startIdx = -1;
        let endIdx = -1;
        let bestProjLatLng = null;

        const count = manualVertices.length >= 3 ? manualVertices.length : manualVertices.length - 1;

        for (let i = 0; i < count; i++) {
          const j = (i + 1) % manualVertices.length;
          const pA = manualVertices[i];
          const pB = manualVertices[j];
          if (!pA || !pB || !isFinite(pA.lat) || !isFinite(pB.lat)) continue;

          const ptA = mapInstance.latLngToLayerPoint([pA.lat, pA.lng]);
          const ptB = mapInstance.latLngToLayerPoint([pB.lat, pB.lng]);

          const dx = ptB.x - ptA.x;
          const dy = ptB.y - ptA.y;
          const l2 = dx * dx + dy * dy;

          if (l2 > 0) {
            const t = ((ptClicked.x - ptA.x) * dx + (ptClicked.y - ptA.y) * dy) / l2;
            // Proyección a lo largo del segmento entre pA y pB
            if (t >= 0.02 && t <= 0.98) {
              const projX = ptA.x + t * dx;
              const projY = ptA.y + t * dy;
              const dist = Math.hypot(ptClicked.x - projX, ptClicked.y - projY);
              if (dist < minPixelDist) {
                minPixelDist = dist;
                bestInsertIdx = i + 1;
                startIdx = i;
                endIdx = j;
                bestProjLatLng = mapInstance.layerPointToLatLng([projX, projY]);
              }
            }
          }
        }

        // Si el toque fue sobre o cerca de cualquier lado de la línea (48px de tolerancia táctil), insertar punto exacto en la línea
        if (minPixelDist <= 48 && bestInsertIdx !== -1) {
          const p1Label = `P${String(startIdx + 1).padStart(2, '0')}`;
          const p2Label = `P${String(endIdx + 1).padStart(2, '0')}`;
          const newLabel = `P${String(bestInsertIdx + 1).padStart(2, '0')}`;
          handleInsertVertexAt(bestProjLatLng || latlng, bestInsertIdx, p1Label, p2Label, newLabel);
          return;
        }
      } catch (err) {
        console.error('Error calculando inserción en arista:', err);
      }
    }"""

maptab_code = re.sub(old_edge_click_pattern, new_edge_click, maptab_code, flags=re.DOTALL)
print("Updated handleMapClick edge detection to 48px with accurate line projection")

# 2d. In JSX: Remove midMarkers (+) loop completely, add interactive={false} to Polygon and Polyline
old_drawing_jsx_pattern = r"\{/\* Elementos de Dibujo Manual en Pantalla.*?\{manualVertices\.map\("
new_drawing_jsx = """{/* Elementos de Dibujo Manual en Pantalla (Admin / Superadmin) */}
        {isManualDrawing && (
          <>
            {manualVertices.length >= 3 && (
              <Polygon
                positions={manualPositions}
                interactive={false}
                pathOptions={{
                  color: '#8b5cf6',
                  fillColor: '#8b5cf6',
                  fillOpacity: 0.22,
                  weight: 2.5
                }}
              />
            )}
            {manualPositions.length >= 2 && (
              <>
                <Polyline
                  positions={manualPositions}
                  interactive={false}
                  pathOptions={{ color: '#8b5cf6', weight: 3, dashArray: '5, 5' }}
                />
                {renderSegmentMeasures(
                  manualVertices, 
                  manualVertices.length >= 3, 
                  '#8b5cf6', 
                  'man-seg',
                  handleInsertVertexAt
                )}
              </>
            )}

            {manualVertices.map("""

maptab_code = re.sub(old_drawing_jsx_pattern, new_drawing_jsx, maptab_code, flags=re.DOTALL)
print("Removed (+) circle markers loop and set interactive={false} on Polygon & Polyline")

# 2e. Replace bottom vertex card with slim, compact card (2 clean rows, height ~76px)
old_bottom_card_pattern = r"\{/\* Tarjeta Flotante Inferior: Vértice Seleccionado al Tocar.*?\{/\* Drawer de Inspección al Tocar un Predio \*/\}"
new_bottom_card = """{/* Tarjeta Flotante Inferior: Vértice Seleccionado (Ultra-Compacta, 2 filas limpias, ~75px) */}
      {isManualDrawing && selectedVertexIndex !== null && manualVertices[selectedVertexIndex] && (
        <div 
          className="selected-vertex-bottom-card"
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1000,
            width: 'calc(100% - 20px)',
            maxWidth: '390px',
            background: 'rgba(255, 255, 255, 0.98)',
            backdropFilter: 'blur(12px)',
            border: '1.5px solid #f59e0b',
            borderRadius: '14px',
            boxShadow: '0 6px 24px rgba(0, 0, 0, 0.25)',
            padding: '8px 12px',
            animation: 'fadeInUp 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px'
          }}
        >
          {/* Fila 1: Badge P0x + Coordenadas Este y Norte en 1 línea + Botón Cerrar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, flex: 1 }}>
              <span style={{
                background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                color: '#ffffff',
                fontWeight: '900',
                fontSize: '11px',
                padding: '2px 7px',
                borderRadius: '6px',
                whiteSpace: 'nowrap'
              }}>
                📍 P{String(selectedVertexIndex + 1).padStart(2, '0')}
              </span>
              <span className="mono" style={{ fontSize: '11px', fontWeight: '800', color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                X: {(manualVertices[selectedVertexIndex].x ?? 0).toFixed(1)} · Y: {(manualVertices[selectedVertexIndex].y ?? 0).toFixed(1)}
              </span>
            </div>

            <button
              type="button"
              onClick={() => setSelectedVertexIndex && setSelectedVertexIndex(null)}
              style={{
                background: '#f1f5f9',
                border: 'none',
                borderRadius: '50%',
                width: '24px',
                height: '24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#64748b',
                cursor: 'pointer',
                flexShrink: 0
              }}
              title="Cerrar"
            >
              <XIcon size={14} />
            </button>
          </div>

          {/* Fila 2: Botones de Acción directos */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              type="button"
              onClick={() => handleOpenEditVertexCoords(selectedVertexIndex)}
              style={{
                flex: 1,
                height: '34px',
                background: 'linear-gradient(135deg, #0284c7, #0369a1)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '11.5px',
                fontWeight: '800',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px'
              }}
            >
              <Edit2 size={13} /> Modificar
            </button>

            <button
              type="button"
              onClick={() => handleConfirmDeleteVertex(selectedVertexIndex)}
              style={{
                flex: 1,
                height: '34px',
                background: '#fee2e2',
                color: '#dc2626',
                border: '1px solid #fca5a5',
                borderRadius: '8px',
                fontSize: '11.5px',
                fontWeight: '800',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px'
              }}
            >
              <Trash2 size={13} /> Eliminar Punto
            </button>
          </div>
        </div>
      )}

      {/* Drawer de Inspección al Tocar un Predio */}"""

maptab_code = re.sub(old_bottom_card_pattern, new_bottom_card, maptab_code, flags=re.DOTALL)
print("Replaced bottom card with sleek 2-row card (~75px)")

with open(maptab_path, "w", encoding="utf-8") as f:
    f.write(maptab_code)
print("Saved clean MapTab.jsx")


print("--- 3. BUMPING VERSION TO v4.6.2 (code 38) ---")
pkg_path = os.path.join(base_dir, "package.json")
with open(pkg_path, "r", encoding="utf-8") as f:
    pkg = json.load(f)
pkg["version"] = "4.6.2"
with open(pkg_path, "w", encoding="utf-8") as f:
    json.dump(pkg, f, indent=2)
print("Updated package.json to v4.6.2")

gradle_path = os.path.join(base_dir, "android", "app", "build.gradle")
with open(gradle_path, "r", encoding="utf-8") as f:
    gradle_code = f.read()
gradle_code = re.sub(r'versionCode\s+\d+', 'versionCode 38', gradle_code)
gradle_code = re.sub(r'versionName\s+"[^"]+"', 'versionName "4.6.2"', gradle_code)
with open(gradle_path, "w", encoding="utf-8") as f:
    f.write(gradle_code)
print("Updated build.gradle to versionCode 38, versionName 4.6.2")

print("=== UI SIMPLIFICATION APPLIED SUCCESSFULLY ===")
