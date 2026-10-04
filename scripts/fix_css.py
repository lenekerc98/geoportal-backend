path = r"c:\LNCZ\proyecto-catastro-2026\movil\src\components\ReportePlanimetrico.css"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

rule = """/* Bloqueo total de gestos en mapas internos del reporte para no desplazar el plano */
.report-map-container .leaflet-container,
.minimap-box .leaflet-container {
  pointer-events: none !important;
  user-select: none !important;
  -webkit-user-select: none !important;
}"""

c = c.replace(rule, "").strip()

marker = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');"
if marker in c:
    c = c.replace(marker, marker + "\n\n" + rule)

with open(path, "w", encoding="utf-8") as f:
    f.write(c + "\n")
print("ReportePlanimetrico.css clean and reordered")
