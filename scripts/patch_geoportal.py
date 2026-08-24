import re

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Geoportal\Geoportal.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscamos donde inyectar el estado inicial para la herramienta de dibujo libre
state_target = '  const [isDrawingPredio, setIsDrawingPredio] = useState(false);'
state_code = '''  const [isDrawingPredio, setIsDrawingPredio] = useState(false);
  const [drawingMode, setDrawingMode] = useState(null); // 'Point', 'Line', 'Polyline', 'Polygon'
  const [freeDrawings, setFreeDrawings] = useState([]); // Array de bosquejos dibujados
'''

if state_target in content and 'const [drawingMode' not in content:
    content = content.replace(state_target, state_code)
    print("Injected state.")

# Inyectamos la barra flotante cerca del modo dibujo
target_toolbar = '        {isDrawingPredio && ('
toolbar_code = '''
        {/* Barra Flotante de Dibujo Libre */}
        <div style={{ position: 'absolute', top: '80px', left: '20px', zIndex: 1000, background: 'var(--bg-panel)', padding: '10px', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.3)', border: '1px solid var(--card-border)' }}>
          <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: 'var(--text-main)' }}>Herramientas de Dibujo</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button onClick={() => setDrawingMode('Point')} className="btn-secondary" style={{ fontSize: '12px', padding: '5px' }}>Punto</button>
            <button onClick={() => setDrawingMode('Line')} className="btn-secondary" style={{ fontSize: '12px', padding: '5px' }}>Línea</button>
            <button onClick={() => setDrawingMode('Polyline')} className="btn-secondary" style={{ fontSize: '12px', padding: '5px' }}>Polilínea</button>
            <button onClick={() => setDrawingMode('Polygon')} className="btn-secondary" style={{ fontSize: '12px', padding: '5px' }}>Polígono</button>
          </div>
          {drawingMode && (
             <div style={{ marginTop: '10px' }}>
               <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Activo: {drawingMode}</span>
               <button onClick={() => setDrawingMode(null)} className="btn-cancel" style={{ fontSize: '10px', marginLeft: '5px', padding: '2px 5px' }}>X</button>
             </div>
          )}
        </div>

        {isDrawingPredio && ('''

if target_toolbar in content and 'Herramientas de Dibujo' not in content:
    content = content.replace(target_toolbar, toolbar_code)
    print("Injected toolbar.")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
