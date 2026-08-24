css_path = r'c:\LNCZ\proyecto-catastro-2026\frontend\src\components\MapViewer\ShapefileAtlasModal.css'

with open(css_path, 'r', encoding='utf-8') as f:
    css = f.read()

target_nav = '''/* Navigation Toolbar */
.atlas-nav-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--card-bg, #ffffff);
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid var(--card-border, #e2e8f0);
}

.atlas-nav-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 6px 8px;
  color: var(--text-main, #334155);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.atlas-nav-btn:hover:not(:disabled) {
  background: var(--sidebar-hover, #f1f5f9);
  border-color: var(--card-border, #cbd5e1);
}

.atlas-nav-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.atlas-nav-status {
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0 8px;
  color: var(--text-main, #1e293b);
  white-space: nowrap;
}'''

replacement_nav = '''/* Navigation Toolbar */
.atlas-nav-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f1f5f9;
  padding: 4px 8px;
  border-radius: 10px;
  border: 1.5px solid #cbd5e1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.atlas-nav-btn {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 10px;
  color: #0284c7;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.atlas-nav-btn:hover:not(:disabled) {
  background: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
  transform: translateY(-1px);
}

.atlas-nav-btn:disabled {
  opacity: 0.35;
  background: transparent;
  border-color: transparent;
  color: #94a3b8;
  cursor: not-allowed;
  box-shadow: none;
}

.atlas-nav-status {
  font-size: 0.9rem;
  font-weight: 800;
  padding: 0 12px;
  color: #0f172a;
  white-space: nowrap;
  letter-spacing: -0.2px;
}'''

if target_nav in css:
    css = css.replace(target_nav, replacement_nav)
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write(css)
    print("Updated navigation toolbar styling in ShapefileAtlasModal.css.")
else:
    print("Target nav CSS not found.")
