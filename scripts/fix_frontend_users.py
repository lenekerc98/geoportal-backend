import re

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Users\Users.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure we import useState, useEffect
# The component is called Users. Let's find formData definition.
# It should have proyectos_ids.
if 'proyectos_ids:' not in content:
    content = content.replace(
        "id_empresa: user?.id_empresa || ''",
        "id_empresa: user?.id_empresa || '',\n        proyectos_ids: user?.proyectos_ids || []"
    )
    content = content.replace(
        "id_empresa: ''",
        "id_empresa: '',\n      proyectos_ids: []"
    )

# Fetch proyectos when opening modal
if 'const [proyectosList, setProyectosList] = useState([]);' not in content:
    content = content.replace(
        "const [roles, setRoles] = useState([]);",
        "const [roles, setRoles] = useState([]);\n  const [proyectosList, setProyectosList] = useState([]);"
    )

# We need to fetch projects. Let's add it to fetchInitialData
if 'setProyectosList(proyRes.data);' not in content:
    fetch_proy_code = '''
      const proyRes = await fetch(`${API_URL}/api/proyectos`, { headers: { 'Authorization': `Bearer ${token}` } });
      if (proyRes.ok) {
        const pData = await proyRes.json();
        setProyectosList(pData);
      }
'''
    # Find where roles are fetched and insert there
    if 'setRoles(rolesData);' in content:
        content = content.replace(
            "setRoles(rolesData);",
            "setRoles(rolesData);" + fetch_proy_code
        )

# Add the UI for selecting projects if role is not admin/superadmin
ui_code = '''
            {/* Project Selection for Regular Users */}
            {formData.id_rol && roles.find(r => r.id_rol === parseInt(formData.id_rol))?.nombre.toLowerCase() !== 'admin' && roles.find(r => r.id_rol === parseInt(formData.id_rol))?.nombre.toLowerCase() !== 'superadmin' && (
              <div style={{ marginTop: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', color: 'gray' }}>Proyectos Asignados</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', background: 'var(--bg-main)', padding: '10px', borderRadius: '5px', border: '1px solid var(--card-border)', maxHeight: '150px', overflowY: 'auto' }}>
                  {proyectosList.filter(p => !formData.id_empresa || p.empresas?.some(e => e.id === parseInt(formData.id_empresa))).map(p => (
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
    # Insert before the submit button
    content = content.replace(
        '<div className="modal-actions">',
        ui_code + '\n            <div className="modal-actions">'
    )

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Frontend Users.jsx modified successfully")
