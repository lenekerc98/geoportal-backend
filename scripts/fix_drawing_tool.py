import os

def patch_file(filepath, target, replacement):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"{os.path.basename(filepath)} modified successfully!")
    else:
        print(f"Could not find the target string in {os.path.basename(filepath)}")

# 1. Patch DrawPolygonTool.jsx
draw_tool_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\MapViewer\DrawPolygonTool.jsx'
target_draw = '''    click(e) {
      if (isDrawing) {
        // Usa el punto con snap si existe, sino el punto del clic
        const pointToAdd = snappedLatLng ? snappedLatLng : e.latlng;
        setDrawPoints(prev => [...prev, pointToAdd]);
      }
    },'''

replacement_draw = '''    click(e) {
      if (isDrawing) {
        // Usa el punto con snap si existe, sino el punto del clic
        const pointToAdd = snappedLatLng ? snappedLatLng : e.latlng;
        setDrawPoints(prev => {
          if (prev.length > 0) {
            const lastPoint = prev[prev.length - 1];
            if (lastPoint.lat === pointToAdd.lat && lastPoint.lng === pointToAdd.lng) {
              return prev; // Evita añadir el mismo punto (ej. en doble clic)
            }
          }
          return [...prev, pointToAdd];
        });
      }
    },'''

patch_file(draw_tool_path, target_draw, replacement_draw)

# 2. Patch Geoportal.jsx
geoportal_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Geoportal\Geoportal.jsx'
target_geo = '''          <MousePointer2 size={18} color="var(--accent-color)" />
          <span style={{ color: 'var(--text-main)', fontWeight: 'bold' }}>Modo Dibujo: Doble clic para finalizar</span>
          <button
            className="btn-cancel"'''

replacement_geo = '''          <MousePointer2 size={18} color="var(--accent-color)" />
          <span style={{ color: 'var(--text-main)', fontWeight: 'bold' }}>Modo Dibujo: Doble clic o clic en Finalizar</span>
          <button
            style={{ padding: '5px 15px', fontSize: '12px', borderRadius: '15px', background: 'var(--accent-color)', color: 'white', border: 'none', cursor: 'pointer' }}
            onClick={() => handleFinishDrawing(drawPoints)}
          >
            Finalizar
          </button>
          <button
            className="btn-cancel"'''

patch_file(geoportal_path, target_geo, replacement_geo)
