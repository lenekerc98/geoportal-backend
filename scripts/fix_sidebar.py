import re

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\Layout\SidebarLayout.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''                      {proyectosList.map(proj => (
                        <option key={proj.id} value={proj.id}>{proj.nombre}</option>
                      ))}'''

replacement = '''                      {proyectosList.filter(proj => !activeEmpresa || proj.empresas_ids?.includes(activeEmpresa.id)).map(proj => (
                        <option key={proj.id} value={proj.id}>{proj.nombre}</option>
                      ))}'''

if target in content:
    content = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SidebarLayout.jsx modified successfully: applied filters!")
else:
    print("Could not find the target string in SidebarLayout.jsx")
