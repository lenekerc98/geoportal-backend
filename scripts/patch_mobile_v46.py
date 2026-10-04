# -*- coding: utf-8 -*-
import os
import re
import json

base_dir = r"c:\LNCZ\proyecto-catastro-2026\movil"

print("--- 1. PATCHING ReportePlanimetricoSheet.jsx ---")
sheet_path = os.path.join(base_dir, "src", "components", "ReportePlanimetricoSheet.jsx")
with open(sheet_path, "r", encoding="utf-8") as f:
    sheet_code = f.read()

# Replace main map props
old_main_map = """                      zoomControl={false}
                      scrollWheelZoom={true}
                      doubleClickZoom={true}
                      dragging={true}
                      touchZoom={true}"""

new_main_map = """                      zoomControl={false}
                      scrollWheelZoom={false}
                      doubleClickZoom={false}
                      dragging={false}
                      touchZoom={false}
                      boxZoom={false}
                      keyboard={false}"""

if old_main_map in sheet_code:
    sheet_code = sheet_code.replace(old_main_map, new_main_map, 1)
    print("Locked main map in ReportePlanimetricoSheet.jsx")
else:
    print("Warning: old_main_map not matched directly, using regex...")
    sheet_code = re.sub(
        r"zoomControl=\{false\}\s*scrollWheelZoom=\{true\}\s*doubleClickZoom=\{true\}\s*dragging=\{true\}\s*touchZoom=\{true\}",
        new_main_map.strip(),
        sheet_code,
        count=1
    )

# Replace minimap props
old_minimap = """                        zoomControl={false}
                        scrollWheelZoom={true}
                        doubleClickZoom={true}
                        dragging={true}
                        touchZoom={true}"""

new_minimap = """                        zoomControl={false}
                        scrollWheelZoom={false}
                        doubleClickZoom={false}
                        dragging={false}
                        touchZoom={false}
                        boxZoom={false}
                        keyboard={false}"""

if old_minimap in sheet_code:
    sheet_code = sheet_code.replace(old_minimap, new_minimap, 1)
    print("Locked minimap in ReportePlanimetricoSheet.jsx")
else:
    print("Warning: old_minimap not matched directly, using regex...")
    sheet_code = re.sub(
        r"zoomControl=\{false\}\s*scrollWheelZoom=\{true\}\s*doubleClickZoom=\{true\}\s*dragging=\{true\}\s*touchZoom=\{true\}",
        new_minimap.strip(),
        sheet_code,
        count=1
    )

with open(sheet_path, "w", encoding="utf-8") as f:
    f.write(sheet_code)
print("Saved ReportePlanimetricoSheet.jsx successfully")


print("--- 2. PATCHING ReportePlanimetricoModal.jsx ---")
modal_path = os.path.join(base_dir, "src", "components", "ReportePlanimetricoModal.jsx")
with open(modal_path, "r", encoding="utf-8") as f:
    modal_code = f.read()

# Add createPortal import
if "createPortal" not in modal_code:
    modal_code = modal_code.replace(
        "import React, { useState, useEffect, useRef } from 'react';",
        "import React, { useState, useEffect, useRef } from 'react';\nimport { createPortal } from 'react-dom';"
    )
    print("Added createPortal import to ReportePlanimetricoModal.jsx")

# Add cleanup effect for print class and afterprint listener
old_back_effect = """    window.addEventListener('androidHardwareBack', handleBack);
    return () => window.removeEventListener('androidHardwareBack', handleBack);
  }, [onClose]);"""

new_back_and_print_effect = """    window.addEventListener('androidHardwareBack', handleBack);
    return () => window.removeEventListener('androidHardwareBack', handleBack);
  }, [onClose]);

  // Limpiar clases de impresión en desmontaje o al terminar de imprimir
  useEffect(() => {
    const handleAfterPrint = () => {
      document.body.classList.remove('is-printing-report');
    };
    window.addEventListener('afterprint', handleAfterPrint);
    return () => {
      document.body.classList.remove('is-printing-report');
      window.removeEventListener('afterprint', handleAfterPrint);
    };
  }, []);"""

if old_back_effect in modal_code:
    modal_code = modal_code.replace(old_back_effect, new_back_and_print_effect, 1)
    print("Added afterprint and cleanup effect to ReportePlanimetricoModal.jsx")

# Update handlePrint to add is-printing-report class and resize trigger
old_handle_print = """  // Imprimir o Guardar como PDF oficial (2 páginas limpias A4)
  const handlePrint = () => {
    setActiveSheet('both');
    const prevZoom = currentZoom;
    setCurrentZoom(1);

    setTimeout(() => {
      const docName = `Reporte_Planimetrico_${predio.codigo || 'Predio'}`;
      if (window.AndroidBridge && typeof window.AndroidBridge.print === 'function') {
        window.AndroidBridge.print(docName);
      } else {
        window.print();
      }

      setTimeout(() => {
        setCurrentZoom(prevZoom);
      }, 1500);
    }, 300);
  };"""

new_handle_print = """  // Imprimir o Guardar como PDF oficial (2 páginas limpias A4)
  const handlePrint = () => {
    setActiveSheet('both');
    const prevZoom = currentZoom;
    setCurrentZoom(1);

    document.body.classList.add('is-printing-report');

    setTimeout(() => {
      // Forzar recálculo de dimensiones en Leaflet a zoom 1
      window.dispatchEvent(new Event('resize'));

      setTimeout(() => {
        const docName = `Reporte_Planimetrico_${predio.codigo || 'Predio'}`;
        if (window.AndroidBridge && typeof window.AndroidBridge.print === 'function') {
          window.AndroidBridge.print(docName);
        } else {
          window.print();
        }

        setTimeout(() => {
          setCurrentZoom(prevZoom);
          document.body.classList.remove('is-printing-report');
        }, 2500);
      }, 350);
    }, 200);
  };"""

if old_handle_print in modal_code:
    modal_code = modal_code.replace(old_handle_print, new_handle_print, 1)
    print("Updated handlePrint in ReportePlanimetricoModal.jsx")
else:
    print("Warning: old_handle_print not matched directly")

# Wrap return with createPortal
if "return createPortal(" not in modal_code:
    modal_code = modal_code.replace(
        "  return (\n    <div \n      className=\"report-modal-overlay\"",
        "  return createPortal(\n    <div \n      className=\"report-modal-overlay\""
    )
    # At the end:
    modal_code = re.sub(
        r"\n    </div>\s*\n  \);\s*\n\}\s*$",
        "\n    </div>,\n    document.body\n  );\n}\n",
        modal_code
    )
    print("Wrapped return with createPortal(..., document.body)")

with open(modal_path, "w", encoding="utf-8") as f:
    f.write(modal_code)
print("Saved ReportePlanimetricoModal.jsx successfully")


print("--- 3. PATCHING ReportePlanimetrico.css ---")
css_path = os.path.join(base_dir, "src", "components", "ReportePlanimetrico.css")
with open(css_path, "r", encoding="utf-8") as f:
    css_code = f.read()

# Add pointer-events none rule for report maps
pointer_rule = """
/* Bloqueo total de gestos en mapas internos del reporte para no desplazar el plano */
.report-map-container .leaflet-container,
.minimap-box .leaflet-container {
  pointer-events: none !important;
  user-select: none !important;
  -webkit-user-select: none !important;
}
"""

if ".report-map-container .leaflet-container" not in css_code:
    css_code = pointer_rule + css_code
    print("Added map pointer-events rule to ReportePlanimetrico.css")

# Overwrite @media print and add body.is-printing-report rules
print_section_marker = "/* REGLAS ESTRICTAS DE IMPRESIÓN Y EXPORTACIÓN PDF OFICIAL A4"
if print_section_marker in css_code:
    idx = css_code.find(print_section_marker)
    base_css = css_code[:idx]
else:
    base_css = css_code

new_print_css = """/* REGLAS ESTRICTAS DE IMPRESIÓN Y EXPORTACIÓN PDF OFICIAL A4 (297mm x 210mm) */
/* ========================================================================= */

/* Al preparar o ejecutar impresión nativa, ocultar TODO el árbol principal (#root) */
body.is-printing-report #root,
body.is-printing-report .app-container,
body.is-printing-report .main-content,
body.is-printing-report .mobile-header,
body.is-printing-report .bottom-nav-bar,
body.is-printing-report .bottom-sheet,
body.is-printing-report .bottom-sheet-backdrop,
body.is-printing-report .swal2-container,
body.is-printing-report .no-print,
body.is-printing-report .report-header-bar,
body.is-printing-report .report-floating-panel,
body.is-printing-report button {
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
  max-height: 0 !important;
  overflow: hidden !important;
  opacity: 0 !important;
}

@media print {
  @page {
    size: 297mm 210mm landscape;
    margin: 0;
  }

  *, *:before, *:after {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  /* Ocultar ABSOLUTAMENTE TODO elemento ajeno a las láminas del reporte */
  #root,
  .app-container,
  .main-content,
  .mobile-header,
  .bottom-nav-bar,
  .bottom-sheet,
  .bottom-sheet-backdrop,
  .swal2-container,
  .no-print,
  .report-header-bar,
  .report-floating-panel,
  .leaflet-control-container,
  .leaflet-top,
  .leaflet-bottom,
  button {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    opacity: 0 !important;
    position: absolute !important;
    left: -99999px !important;
  }

  html, body {
    width: 297mm !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    background: #ffffff !important;
    overflow: visible !important;
  }

  /* El modal montado vía Portal en body es el único contenido visible */
  .report-modal-overlay {
    position: static !important;
    inset: auto !important;
    width: 297mm !important;
    height: auto !important;
    min-height: 0 !important;
    overflow: visible !important;
    background: #ffffff !important;
    display: block !important;
    padding: 0 !important;
    margin: 0 !important;
    z-index: auto !important;
    visibility: visible !important;
  }

  .report-sheets-scroll-area {
    overflow: visible !important;
    background: #ffffff !important;
    padding: 0 !important;
    margin: 0 !important;
    height: auto !important;
    display: block !important;
    visibility: visible !important;
  }

  .report-sheets-zoom-wrapper {
    zoom: 1 !important;
    transform: none !important;
    width: 297mm !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
    display: block !important;
    background: #ffffff !important;
    visibility: visible !important;
  }

  .report-print-container {
    gap: 0 !important;
    display: block !important;
    width: 297mm !important;
    margin: 0 !important;
    padding: 0 !important;
    background: #ffffff !important;
    visibility: visible !important;
  }

  /* Ambas láminas (Pág 1 y Pág 2) se fuerzan a imprimir en páginas separadas */
  .hide-on-screen {
    display: flex !important;
    visibility: visible !important;
  }

  /* Formato exacto 1:1 de cada lámina A4 apaisada (297mm x 209mm) */
  .print-page {
    width: 297mm !important;
    height: 209mm !important;
    min-height: 209mm !important;
    max-height: 209mm !important;
    margin: 0 !important;
    padding: 8mm !important;
    box-sizing: border-box !important;
    background: #ffffff !important;
    box-shadow: none !important;
    overflow: hidden !important;
    position: relative !important;
    display: flex !important;
    visibility: visible !important;
    flex-direction: column !important;
    page-break-after: always !important;
    break-after: page !important;
    page-break-inside: avoid !important;
    break-inside: avoid !important;
  }

  .print-page + .print-page {
    page-break-before: always !important;
    break-before: page !important;
  }

  .print-page:last-child {
    page-break-after: avoid !important;
    break-after: avoid !important;
  }
}
"""

css_code = base_css.rstrip() + "\n\n/* ========================================================================= */\n" + new_print_css

with open(css_path, "w", encoding="utf-8") as f:
    f.write(css_code)
print("Saved ReportePlanimetrico.css successfully")


print("--- 4. PATCHING MapTab.jsx ---")
maptab_path = os.path.join(base_dir, "src", "pages", "MapTab", "MapTab.jsx")
with open(maptab_path, "r", encoding="utf-8") as f:
    maptab_code = f.read()

# 4a. Update manualVertexIcon to sleek clean pin
old_vertex_icon_pattern = r"// Icono para los vértices del dibujo manual.*?const manualVertexIcon = \(num, isSelected = false.*?\n\};\n\n"
new_vertex_icon = """// Icono para los vértices del dibujo manual en pantalla (Normal y Seleccionado)
// Diseño limpio, elegante y profesional: pin circular/pill P01, P02... sin cajas gigantes de texto
// Con vástago y aguja exacta de elevación (~1cm) para que el dedo no tape el terreno ni el vértice
const manualVertexIcon = (num, isSelected = false) => {
  const label = 'P' + String(num).padStart(2, '0');
  const color = isSelected ? '#f59e0b' : '#8b5cf6';
  const width = isSelected ? 36 : 32;
  const height = isSelected ? 40 : 36;

  return L.divIcon({
    className: 'manual-vertex-marker' + (isSelected ? ' selected-vertex' : ''),
    html: `
      <div style="position: relative; width: ${width}px; height: ${height}px; display: flex; flex-direction: column; align-items: center; pointer-events: auto; cursor: pointer;">
        <!-- Placa compacta circular/pill con el identificador P01, P02... -->
        <div style="
          background: ${color}; 
          color: #ffffff; 
          padding: 2px 5px; 
          border-radius: 999px; 
          display: flex; 
          align-items: center; 
          justify-content: center; 
          border: 2px solid #ffffff; 
          box-shadow: ${isSelected ? '0 0 14px #f59e0b, 0 3px 8px rgba(0,0,0,0.5)' : '0 2px 6px rgba(0,0,0,0.35)'}; 
          transform: ${isSelected ? 'scale(1.15)' : 'scale(1)'}; 
          transition: transform 0.15s ease, box-shadow 0.15s ease; 
          white-space: nowrap; 
          z-index: 2;
        ">
          <div style="font-size: 10.5px; font-weight: 900; line-height: 1; letter-spacing: -0.2px;">
            ${label}
          </div>
        </div>
        <!-- Vástago vertical (offset para visibilidad de terreno) -->
        <div style="width: 2px; height: 13px; background: ${color}; box-shadow: 0 0 2px #ffffff; margin-top: -1px; z-index: 1;"></div>
        <!-- Punta/Aguja exacta del punto en el terreno (coordenada precisa) -->
        <div style="width: 6px; height: 6px; background: #ffffff; border: 2px solid ${color}; border-radius: 50%; box-shadow: 0 0 4px rgba(0,0,0,0.6); margin-top: -1px; z-index: 1;"></div>
      </div>
    `,
    iconSize: [width, height],
    iconAnchor: [width / 2, height]
  });
};

"""

maptab_code = re.sub(old_vertex_icon_pattern, new_vertex_icon, maptab_code, flags=re.DOTALL)
print("Updated manualVertexIcon in MapTab.jsx")

# 4b. Add handleConfirmDeleteVertex
old_delete_func = """  // Eliminar vértice individual del dibujo y renumerar correlativamente
  const handleDeleteDrawingVertex = (idx) => {
    if (idx < 0 || idx >= manualVertices.length) return;
    const pCode = 'P' + String(idx + 1).padStart(2, '0');
    setManualVertices(prev => {
      const remaining = prev.filter((_, i) => i !== idx);
      return remaining.map((v, i) => ({
        ...v,
        orden: i + 1
      }));
    });
    if (setSelectedVertexIndex) setSelectedVertexIndex(null);
    if (showToast) {
      showToast({
        type: 'info',
        title: `🗑️ Vértice ${pCode} Eliminado`,
        message: 'El punto fue eliminado y los vértices siguientes se renumeraron automáticamente.',
        duration: 3500
      });
    }
  };"""

new_delete_func = """  // Eliminar vértice individual del dibujo y renumerar correlativamente
  const handleDeleteDrawingVertex = (idx) => {
    if (idx < 0 || idx >= manualVertices.length) return;
    const pCode = 'P' + String(idx + 1).padStart(2, '0');
    setManualVertices(prev => {
      const remaining = prev.filter((_, i) => i !== idx);
      return remaining.map((v, i) => ({
        ...v,
        orden: i + 1
      }));
    });
    if (setSelectedVertexIndex) setSelectedVertexIndex(null);
    if (showToast) {
      showToast({
        type: 'info',
        title: `🗑️ Vértice ${pCode} Eliminado`,
        message: 'El punto fue eliminado y los vértices siguientes se renumeraron automáticamente.',
        duration: 3500
      });
    }
  };

  // Confirmación interactiva con SweetAlert2 para eliminar vértice
  const handleConfirmDeleteVertex = async (idx) => {
    if (idx < 0 || idx >= manualVertices.length) return;
    const pCode = 'P' + String(idx + 1).padStart(2, '0');

    const res = await Swal.fire({
      title: `¿Eliminar Vértice ${pCode}?`,
      text: `El vértice ${pCode} será eliminado y los puntos siguientes se re-numerarán correlativamente (P01, P02...).`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#ef4444',
      cancelButtonColor: '#64748b',
      background: '#ffffff',
      color: '#0f172a'
    });

    if (res.isConfirmed) {
      handleDeleteDrawingVertex(idx);
    }
  };"""

if old_delete_func in maptab_code:
    maptab_code = maptab_code.replace(old_delete_func, new_delete_func, 1)
    print("Added handleConfirmDeleteVertex to MapTab.jsx")
else:
    print("Warning: old_delete_func not matched verbatim")

# 4c. Update manualVertices.map: remove bulky Tooltip and use clean Marker
old_manual_map_pattern = r"\{manualVertices\.map\(\(v, i\) => \(\s*\(isFinite\(v\.lat\) && isFinite\(v\.lng\)\) \? \(\s*<Marker\s+key=\{`manual-\$\{i\}`\}.*?</Marker>\s*\) : null\s*\)\)\}"
new_manual_map = """{manualVertices.map((v, i) => (
              (isFinite(v.lat) && isFinite(v.lng)) ? (
                <Marker
                  key={`manual-${i}`}
                  position={[v.lat, v.lng]}
                  draggable={isManualDrawing}
                  icon={manualVertexIcon(i + 1, selectedVertexIndex === i)}
                  eventHandlers={{
                    click: (e) => {
                      L.DomEvent.stopPropagation(e);
                      if (setSelectedVertexIndex) {
                        setSelectedVertexIndex(selectedVertexIndex === i ? null : i);
                      }
                    },
                    dragstart: () => {
                      if (setSelectedVertexIndex) setSelectedVertexIndex(i);
                    },
                    dragend: (e) => {
                      const newLatLng = e.target.getLatLng();
                      const utm = wgs84ToUtm(newLatLng.lng, newLatLng.lat);
                      const newX = Math.round(utm.x * 100) / 100;
                      const newY = Math.round(utm.y * 100) / 100;
                      setManualVertices(prev => {
                        const copy = [...prev];
                        if (copy[i]) {
                          copy[i] = {
                            ...copy[i],
                            lat: newLatLng.lat,
                            lng: newLatLng.lng,
                            x: newX,
                            y: newY
                          };
                        }
                        return copy;
                      });
                      if (showToast) {
                        showToast({
                          type: 'success',
                          title: `📍 P${String(i + 1).padStart(2, '0')} Reposicionado`,
                          message: `X: ${newX.toFixed(2)} | Y: ${newY.toFixed(2)}`,
                          duration: 2500
                        });
                      }
                    }
                  }}
                />
              ) : null
            ))}"""

maptab_code = re.sub(old_manual_map_pattern, new_manual_map, maptab_code, flags=re.DOTALL)
print("Updated manualVertices.map in MapTab.jsx")

# 4d. Replace top floating bar with bottom Action Card
old_top_bar_pattern = r"\{/\* Barra Flotante Superior: Modificación de Vértice Seleccionado \*/\}\s*\{isManualDrawing && selectedVertexIndex !== null && manualVertices\[selectedVertexIndex\] && \(.*?\)\}\s*\{/\* Drawer de Inspección al Tocar un Predio \*/\}"

new_bottom_card = """{/* Tarjeta Flotante Inferior: Vértice Seleccionado al Tocar (Coordenadas y Acciones Inmediatas) */}
      {isManualDrawing && selectedVertexIndex !== null && manualVertices[selectedVertexIndex] && (
        <div 
          className="selected-vertex-bottom-card"
          style={{
            position: 'absolute',
            bottom: '16px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1000,
            width: 'calc(100% - 24px)',
            maxWidth: '380px',
            background: 'rgba(255, 255, 255, 0.98)',
            backdropFilter: 'blur(10px)',
            border: '2px solid #f59e0b',
            borderRadius: '16px',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.35)',
            padding: '12px 14px',
            animation: 'fadeInUp 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}
        >
          {/* Cabecera con Badge del punto y Botón Cerrar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                color: '#ffffff',
                fontWeight: '900',
                fontSize: '12.5px',
                padding: '3px 9px',
                borderRadius: '8px',
                boxShadow: '0 2px 6px rgba(245, 158, 11, 0.4)',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                📍 Vértice P{String(selectedVertexIndex + 1).padStart(2, '0')}
              </span>
              <span style={{ fontSize: '11px', color: '#64748b', fontWeight: '600' }}>
                Punto {selectedVertexIndex + 1} de {manualVertices.length}
              </span>
            </div>

            <button
              type="button"
              onClick={() => setSelectedVertexIndex && setSelectedVertexIndex(null)}
              style={{
                background: '#f1f5f9',
                border: 'none',
                borderRadius: '50%',
                width: '28px',
                height: '28px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#64748b',
                cursor: 'pointer'
              }}
              title="Cerrar"
            >
              <XIcon size={16} />
            </button>
          </div>

          {/* Coordenadas UTM y Geográficas */}
          <div style={{
            background: '#f8fafc',
            borderRadius: '10px',
            padding: '8px 10px',
            border: '1px solid #e2e8f0',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '6px'
          }}>
            <div>
              <div style={{ fontSize: '9px', color: '#64748b', fontWeight: '700' }}>ESTE (X) - METROS</div>
              <div className="mono" style={{ fontSize: '13px', fontWeight: '800', color: '#0f172a' }}>
                {(manualVertices[selectedVertexIndex].x ?? 0).toFixed(2)} m
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: '#64748b', fontWeight: '700' }}>NORTE (Y) - METROS</div>
              <div className="mono" style={{ fontSize: '13px', fontWeight: '800', color: '#0f172a' }}>
                {(manualVertices[selectedVertexIndex].y ?? 0).toFixed(2)} m
              </div>
            </div>
            <div style={{ gridColumn: 'span 2', borderTop: '1px solid #e2e8f0', paddingTop: '4px', fontSize: '9.5px', color: '#64748b' }}>
              Lat: {Number(manualVertices[selectedVertexIndex].lat || 0).toFixed(6)}° · Lng: {Number(manualVertices[selectedVertexIndex].lng || 0).toFixed(6)}°
            </div>
          </div>

          {/* Botones de Acción Inmediatos y Claros */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              onClick={() => handleOpenEditVertexCoords(selectedVertexIndex)}
              style={{
                flex: 1,
                height: '38px',
                background: 'linear-gradient(135deg, #0284c7, #0369a1)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '10px',
                fontSize: '12px',
                fontWeight: '800',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                boxShadow: '0 2px 8px rgba(2, 132, 199, 0.35)'
              }}
            >
              <Edit2 size={15} /> Modificar
            </button>

            <button
              type="button"
              onClick={() => handleConfirmDeleteVertex(selectedVertexIndex)}
              style={{
                flex: 1,
                height: '38px',
                background: '#fee2e2',
                color: '#dc2626',
                border: '1.5px solid #fca5a5',
                borderRadius: '10px',
                fontSize: '12px',
                fontWeight: '800',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                boxShadow: '0 2px 6px rgba(220, 38, 38, 0.15)'
              }}
            >
              <Trash2 size={15} /> Eliminar Punto
            </button>
          </div>
        </div>
      )}

      {/* Drawer de Inspección al Tocar un Predio */}"""

maptab_code = re.sub(old_top_bar_pattern, new_bottom_card, maptab_code, flags=re.DOTALL)
print("Replaced top bar with bottom Action Card in MapTab.jsx")

with open(maptab_path, "w", encoding="utf-8") as f:
    f.write(maptab_code)
print("Saved MapTab.jsx successfully")


print("--- 5. BUMPING VERSIONS TO v4.6 (code 36) ---")
pkg_path = os.path.join(base_dir, "package.json")
with open(pkg_path, "r", encoding="utf-8") as f:
    pkg = json.load(f)
pkg["version"] = "4.6.0"
with open(pkg_path, "w", encoding="utf-8") as f:
    json.dump(pkg, f, indent=2)
print("Updated package.json to v4.6.0")

gradle_path = os.path.join(base_dir, "android", "app", "build.gradle")
with open(gradle_path, "r", encoding="utf-8") as f:
    gradle_code = f.read()
gradle_code = re.sub(r'versionCode\s+\d+', 'versionCode 36', gradle_code)
gradle_code = re.sub(r'versionName\s+"[^"]+"', 'versionName "4.6"', gradle_code)
with open(gradle_path, "w", encoding="utf-8") as f:
    f.write(gradle_code)
print("Updated build.gradle to versionCode 36, versionName 4.6")

print("=== ALL PATCHES APPLIED SUCCESSFULLY ===")
