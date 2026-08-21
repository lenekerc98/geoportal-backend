import re

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\Users\Users.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix Autofill on Username
content = content.replace(
    '''<input type="text" value={formData.username} onChange={e => setFormData({...formData, username: e.target.value})} required className="input-dynamic" />''',
    '''<input type="text" value={formData.username} onChange={e => setFormData({...formData, username: e.target.value})} required className="input-dynamic" autoComplete="off" />'''
)

# Fix Autofill on Password
content = content.replace(
    '''<input type="password" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} required={isCreating} className="input-dynamic" />''',
    '''<input type="password" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} required={isCreating} className="input-dynamic" autoComplete="new-password" />'''
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Users.jsx modified successfully: Autofill disabled!")
