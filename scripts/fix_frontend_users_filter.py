import re

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Users\Users.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the wrong filtering condition
wrong_filter = "p.empresas?.some(e => e.id === parseInt(formData.id_empresa))"
correct_filter = "p.empresas_ids?.includes(parseInt(formData.id_empresa))"

if wrong_filter in content:
    content = content.replace(wrong_filter, correct_filter)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Users.jsx modified successfully: fixed filter logic!")
else:
    print("Could not find the wrong filter in Users.jsx")
