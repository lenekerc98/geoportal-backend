import re

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Users\Users.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: token -> authToken
content = content.replace(
    "const proyRes = await fetch(`${API_URL}/api/proyectos`, { headers: { 'Authorization': `Bearer ${token}` } });",
    "const proyRes = await fetch(`${API_URL}/api/proyectos`, { headers: { 'Authorization': `Bearer ${authToken}` } });"
)

# Fix 2: Inject UI
ui_code = '''
              {/* Project Selection for Regular Users */}
              {formData.id_rol && roles.find(r => r.id_rol === parseInt(formData.id_rol))?.nombre.toLowerCase() !== 'admin' && roles.find(r => r.id_rol === parseInt(formData.id_rol))?.nombre.toLowerCase() !== 'superadmin' && (
                <div style={{ marginBottom: '30px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Proyectos Asignados</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', background: 'var(--bg-main)', padding: '10px', borderRadius: '5px', border: '1px solid var(--card-border)', maxHeight: '150px', overflowY: 'auto' }}>
                    {proyectosList.filter(p => !formData.id_empresa || p.empresas_ids?.includes(parseInt(formData.id_empresa))).map(p => (
                      <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '14px' }}>
                        <input 
                          type="checkbox" 
                          checked={formData.proyectos_ids?.includes(p.id)}
                          onChange={(e) => {
                            const isChecked = e.target.checked;
                            setFormData(prev => ({
                              ...prev,
                              proyectos_ids: isChecked 
                                ? [...(prev.proyectos_ids || []), p.id] 
                                : (prev.proyectos_ids || []).filter(id => id !== p.id)
                            }));
                          }}
                          style={{ cursor: 'pointer' }}
                        />
                        {p.nombre}
                      </label>
                    ))}
                    {proyectosList.length === 0 && <span style={{ fontSize: '12px', color: 'gray' }}>No hay proyectos disponibles</span>}
                  </div>
                </div>
              )}
'''

if 'Proyectos Asignados' not in content:
    content = content.replace(
        "<div style={{ display: 'flex', gap: '15px', justifyContent: 'flex-end' }}>",
        ui_code + "\n              <div style={{ display: 'flex', gap: '15px', justifyContent: 'flex-end' }}>"
    )

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Users.jsx modified successfully: final fixes applied!")
