import re

filepath = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\pages\System\SystemParams.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if 'const [logoFile, setLogoFile] = useState(null);' not in content:
    content = content.replace("const [activeTab, setActiveTab] = useState('empresa');", "const [activeTab, setActiveTab] = useState('empresa');\n  const [logoFile, setLogoFile] = useState(null);")

new_submit = '''  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!activeEmpresa) return;
    setIsSaving(true);
    try {
      const token = localStorage.getItem('catastro_token');
      const isBase64 = empresaConfig.logo_url && empresaConfig.logo_url.startsWith('data:');
      
      const updateData = {
          parametros: { ...activeEmpresa.parametros, modo_historico: empresaConfig.modo_historico },
          logo_url: isBase64 ? activeEmpresa.logo_url : (empresaConfig.logo_url || null),
          nombre_alcalde: empresaConfig.nombre_alcalde || null,
          nombre_director: empresaConfig.nombre_director || null,
          sbu_actual: empresaConfig.sbu_actual ? parseFloat(empresaConfig.sbu_actual) : null,
          valor_m2_urbano: empresaConfig.valor_m2_urbano ? parseFloat(empresaConfig.valor_m2_urbano) : null,
          valor_m2_rural: empresaConfig.valor_m2_rural ? parseFloat(empresaConfig.valor_m2_rural) : null
      };
      
      const res = await fetch(`${API_URL}/api/empresas/${activeEmpresa.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(updateData)
      });
      
      if (res.ok) {
        let updatedEmpresa = await res.json();
        
        if (logoFile) {
          const fileData = new FormData();
          fileData.append('logo', logoFile);
          
          const uploadRes = await fetch(`${API_URL}/api/empresas/${activeEmpresa.id}/upload-images`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: fileData
          });
          
          if (uploadRes.ok) {
            updatedEmpresa = await uploadRes.json();
          }
        }
        
        setGlobalEmpresa(updatedEmpresa);
        setLogoFile(null);
        showSuccess('Configuración guardada exitosamente');
      } else {
        const err = await res.json();
        showError(err.detail || 'Error al guardar');
      }
    } catch(e) {
      showError('Error de conexión');
    } finally {
      setIsSaving(false);
    }
  };'''

content = re.sub(r'  const handleSubmit = async \(e\) => \{.*?^\s*};\n', new_submit + '\n', content, flags=re.MULTILINE|re.DOTALL)

old_onchange = '''                        onChange={(e) => {
                          const file = e.target.files[0];
                          if (file) {
                            const reader = new FileReader();
                            reader.onload = (event) => {
                              setEmpresaConfig({...empresaConfig, logo_url: event.target.result});
                            };
                            reader.readAsDataURL(file);
                          }
                        }}'''

new_onchange = '''                        onChange={(e) => {
                          const file = e.target.files[0];
                          if (file) {
                            setLogoFile(file);
                            const reader = new FileReader();
                            reader.onload = (event) => {
                              setEmpresaConfig({...empresaConfig, logo_url: event.target.result});
                            };
                            reader.readAsDataURL(file);
                          }
                        }}'''

content = content.replace(old_onchange, new_onchange)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("frontend modified successfully")
