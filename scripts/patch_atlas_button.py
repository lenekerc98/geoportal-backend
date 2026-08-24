geoportal_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Geoportal\Geoportal.jsx'

with open(geoportal_path, 'r', encoding='utf-8') as f:
    gp_content = f.read()

target = '''                    <button className="btn-primary" onClick={() => setShowShapefileUploader(true)} style={{ flex: 1, padding: '8px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }} title="Subir Shapefile (Catastro o Adicional)">
                      <UploadCloud size={16} /> Shapefile
                    </button>'''

replacement = '''                    <button className="btn-primary" onClick={() => shapefileInputRef.current?.click()} style={{ flex: 1, padding: '8px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }} title="Subir Shapefile para Asistente Atlas">
                      <UploadCloud size={16} /> Shapefile Atlas
                    </button>
                    <button className="btn-primary" onClick={() => setShowShapefileUploader(true)} style={{ padding: '8px 10px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }} title="Subir Shapefile a Tablas Crudas / BD">
                      <Database size={16} />
                    </button>'''

atlas_banner = '''                  {importedShapes && (
                    <button 
                      onClick={() => setShowAtlasModal(true)} 
                      style={{ width: '100%', marginBottom: '10px', padding: '8px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', background: 'linear-gradient(135deg, #0284c7, #0369a1)', color: '#fff', fontWeight: 'bold', borderRadius: '8px', border: 'none', cursor: 'pointer', boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)' }}
                    >
                      <Sparkles size={16} /> 📖 Ver Atlas de Shapefile ({importedShapes.features?.length || 0})
                    </button>
                  )}
'''

if target in gp_content and '📖 Ver Atlas de Shapefile' not in gp_content:
    gp_content = gp_content.replace(target, replacement + '\n' + atlas_banner)
    with open(geoportal_path, 'w', encoding='utf-8') as f:
        f.write(gp_content)
    print("Added Atlas button to Geoportal sidebar.")
else:
    print("Target already modified or not found.")
