import re

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\MapViewer\PredioForm.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the fetch call in buscarCodigo
old_fetch = "const res = await fetch(`${API_URL}/api/gis/codigos/buscar/${formData.cod_catastral}`, {"
new_fetch = """const codParaBuscar = encodeURIComponent(formData.cod_catastral.replace(/\\s/g, ''));
      const res = await fetch(`${API_URL}/api/gis/codigos/buscar/${codParaBuscar}`, {"""

if old_fetch in content:
    content = content.replace(old_fetch, new_fetch)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("PredioForm.jsx modified successfully!")
else:
    print("Could not find the fetch call to replace.")
