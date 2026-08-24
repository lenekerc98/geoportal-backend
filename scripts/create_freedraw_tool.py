import os

js_code = """import React, { useState, useEffect } from 'react';
import { useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import Swal from 'sweetalert2';
import proj4 from 'proj4';

if (!proj4.defs('EPSG:32717')) {
  proj4.defs('EPSG:32717', '+proj=utm +zone=17 +south +datum=WGS84 +units=m +no_defs');
}

export default function FreeDrawTool({ 
  drawingMode, 
  setDrawingMode, 
  onDrawingComplete, 
  drawPoints, 
  setDrawPoints, 
  setMousePos 
}) {
  const [snappedLatLng, setSnappedLatLng] = useState(null);
  const [cachedSnapPoints, setCachedSnapPoints] = useState([]);
  const map = useMap();

  useEffect(() => {
    if (drawingMode) {
      map.doubleClickZoom.disable();
      const points = [];
      map.eachLayer((layer) => {
        if (layer.getLatLngs) {
          const latlngs = layer.getLatLngs();
          const extract = (coords) => {
            coords.forEach(coord => {
              if (Array.isArray(coord)) {
                extract(coord);
              } else if (coord && coord.lat !== undefined && coord.lng !== undefined) {
                points.push(coord);
              }
            });
          };
          extract(latlngs);
        }
      });
      setCachedSnapPoints(points);
    } else {
      map.doubleClickZoom.enable();
      setCachedSnapPoints([]);
      setDrawPoints([]);
      setMousePos(null);
    }
  }, [drawingMode, map]);

  const finishDrawing = (pointsToUse) => {
    if (!drawingMode) return;
    const pts = pointsToUse || drawPoints;
    
    if (drawingMode === 'Point' && pts.length >= 1) {
      const pt = pts[0];
      const feature = {
        type: 'Feature',
        id: 'draw_' + Date.now(),
        geometry: {
          type: 'Point',
          coordinates: [pt.lng, pt.lat]
        },
        properties: {
          tipo: 'Point',
          fecha: new Date().toISOString(),
          nombre: `Punto #${Date.now().toString().slice(-4)}`
        }
      };
      onDrawingComplete(feature);
    } else if (drawingMode === 'Line' && pts.length >= 2) {
      const linePts = pts.slice(0, 2);
      const feature = {
        type: 'Feature',
        id: 'draw_' + Date.now(),
        geometry: {
          type: 'LineString',
          coordinates: linePts.map(p => [p.lng, p.lat])
        },
        properties: {
          tipo: 'Line',
          fecha: new Date().toISOString(),
          nombre: `Línea #${Date.now().toString().slice(-4)}`
        }
      };
      onDrawingComplete(feature);
    } else if (drawingMode === 'Polyline' && pts.length >= 2) {
      const feature = {
        type: 'Feature',
        id: 'draw_' + Date.now(),
        geometry: {
          type: 'LineString',
          coordinates: pts.map(p => [p.lng, p.lat])
        },
        properties: {
          tipo: 'Polyline',
          fecha: new Date().toISOString(),
          nombre: `Polilínea #${Date.now().toString().slice(-4)}`
        }
      };
      onDrawingComplete(feature);
    } else if (drawingMode === 'Polygon' && pts.length >= 3) {
      const closedCoords = pts.map(p => [p.lng, p.lat]);
      if (closedCoords[0][0] !== closedCoords[closedCoords.length - 1][0] || closedCoords[0][1] !== closedCoords[closedCoords.length - 1][1]) {
        closedCoords.push(closedCoords[0]);
      }
      const feature = {
        type: 'Feature',
        id: 'draw_' + Date.now(),
        geometry: {
          type: 'Polygon',
          coordinates: [closedCoords]
        },
        properties: {
          tipo: 'Polygon',
          fecha: new Date().toISOString(),
          nombre: `Polígono #${Date.now().toString().slice(-4)}`
        }
      };
      onDrawingComplete(feature);
    }
    
    setDrawPoints([]);
    setMousePos(null);
  };

  useMapEvents({
    click(e) {
      if (!drawingMode) return;
      const pointToAdd = snappedLatLng ? snappedLatLng : e.latlng;
      
      if (drawingMode === 'Point') {
        finishDrawing([pointToAdd]);
        return;
      }
      
      if (drawingMode === 'Line') {
        const next = [...drawPoints, pointToAdd];
        if (next.length >= 2) {
          finishDrawing(next);
        } else {
          setDrawPoints(next);
        }
        return;
      }
      
      // Polyline / Polygon
      setDrawPoints(prev => {
        if (prev.length > 0) {
          const last = prev[prev.length - 1];
          if (last.lat === pointToAdd.lat && last.lng === pointToAdd.lng) return prev;
        }
        return [...prev, pointToAdd];
      });
    },
    mousemove(e) {
      if (!drawingMode) {
        setMousePos(null);
        return;
      }
      
      let bestSnap = null;
      let minDistance = 20;
      const mousePoint = map.latLngToLayerPoint(e.latlng);
      
      if (cachedSnapPoints.length > 0) {
        cachedSnapPoints.forEach(coord => {
          const vPoint = map.latLngToLayerPoint(coord);
          const dist = mousePoint.distanceTo(vPoint);
          if (dist < minDistance) {
            minDistance = dist;
            bestSnap = coord;
          }
        });
      }
      
      if (bestSnap) {
        setSnappedLatLng(bestSnap);
        setMousePos(bestSnap);
      } else {
        setSnappedLatLng(null);
        setMousePos(e.latlng);
      }
    },
    dblclick(e) {
      if (!drawingMode) return;
      L.DomEvent.stopPropagation(e);
      L.DomEvent.preventDefault(e);
      finishDrawing(drawPoints);
    }
  });

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!drawingMode) return;
      if (e.key === 'Escape') {
        e.preventDefault();
        setDrawingMode(null);
        setDrawPoints([]);
        setMousePos(null);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        finishDrawing(drawPoints);
      } else if (e.ctrlKey && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        setDrawPoints(prev => prev.slice(0, -1));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [drawingMode, drawPoints]);

  useEffect(() => {
    const container = map.getContainer();
    if (drawingMode) {
      container.style.cursor = 'crosshair';
    } else {
      container.style.cursor = '';
    }
    return () => {
      container.style.cursor = '';
    };
  }, [drawingMode, map]);

  return null;
}
"""

target_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\MapViewer\FreeDrawTool.jsx'
with open(target_path, 'w', encoding='utf-8') as f:
    f.write(js_code)

print("Generated FreeDrawTool.jsx successfully.")
