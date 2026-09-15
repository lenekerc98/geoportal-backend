# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT PARA QGIS: POLIGONIZAR LÍNEAS Y ASIGNAR POSESIONARIOS DESDE PUNTOS (CAD/SHP)
===============================================================================
Este script resuelve el caso típico donde en CAD o Shapefile tienes:
  1. Los linderos o bordes del predio como líneas (LineString).
  2. Los nombres de los posesionarios (o códigos catastrales) como puntos de texto.

¿Qué hace este script?
  1. Poligoniza las líneas cerradas para formar polígonos (predios).
  2. Realiza un Spatial Join (unión espacial) asignando a cada polígono el texto
     del punto que cae dentro de su perímetro.
  3. Añade la capa resultante lista con su tabla de atributos a QGIS, o la exporta
     a un nuevo Shapefile.

INSTRUCCIONES DE USO EN QGIS:
  1. Abre QGIS.
  2. Abre la consola de Python: Menú Complementos > Consola de Python (Ctrl + Alt + P).
  3. Haz clic en el ícono del bloc de notas ("Mostrar editor") para abrir el editor.
  4. Pega este código o abre este archivo .py.
  5. Ajusta los nombres de tus capas en las variables de configuración abajo.
  6. Presiona el botón verde de "Play" (Ejecutar script).
===============================================================================
"""

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsProcessingException
)
import processing

# =============================================================================
# CONFIGURACIÓN (Ajusta estos valores según tus capas cargadas en QGIS)
# =============================================================================
NOMBRE_CAPA_LINEAS = "lineas"       # Nombre exacto de tu capa de linderos/líneas en QGIS
NOMBRE_CAPA_PUNTOS = "puntos"       # Nombre exacto de tu capa de puntos con textos
CAMPO_TEXTO_POSESIONARIO = "text"   # Nombre de la columna donde viene el texto (ej: "text", "TEXT", "STRING", "nombre")

TOLERANCIA_SNAP_METROS = 0.05       # 0.05 m (5 cm) para cerrar micro-huecos en esquinas CAD. Pon 0 para desactivar.
EXPORTAR_A_ARCHIVO = None           # Ej: r"C:\LNCZ\predios_finales.shp" o None para capa en memoria
# =============================================================================

def ejecutar_proceso():
    project = QgsProject.instance()
    
    # 1. Buscar las capas en el proyecto de QGIS
    capas_lineas = project.mapLayersByName(NOMBRE_CAPA_LINEAS)
    capas_puntos = project.mapLayersByName(NOMBRE_CAPA_PUNTOS)
    
    if not capas_lineas:
        print(f"❌ [ERROR] No se encontró la capa de líneas llamada: '{NOMBRE_CAPA_LINEAS}'")
        print("👉 Capas disponibles en tu QGIS:")
        for lyr in project.mapLayers().values():
            print(f"   - {lyr.name()} ({lyr.geometryType()})")
        return
        
    if not capas_puntos:
        print(f"❌ [ERROR] No se encontró la capa de puntos llamada: '{NOMBRE_CAPA_PUNTOS}'")
        return
        
    capa_lineas = capas_lineas[0]
    capa_puntos = capas_puntos[0]
    
    print("="*60)
    print(f"🚀 INICIANDO CONVERSIÓN CATASTRAL")
    print(f"📍 Capa de líneas: '{capa_lineas.name()}' ({capa_lineas.featureCount()} entidades)")
    print(f"📍 Capa de puntos: '{capa_puntos.name()}' ({capa_puntos.featureCount()} textos)")
    print("="*60)
    
    lineas_a_usar = capa_lineas

    # 2. Snap opcional si las líneas no intersectan exactamente en los vértices
    if TOLERANCIA_SNAP_METROS > 0:
        print(f"📐 Paso 1/3: Aplicando snap de nodos ({TOLERANCIA_SNAP_METROS}m) para cerrar linderos CAD...")
        try:
            res_snap = processing.run("native:snapgeometries", {
                'INPUT': capa_lineas,
                'REFERENCE_LAYER': capa_lineas,
                'TOLERANCE': TOLERANCIA_SNAP_METROS,
                'BEHAVIOR': 0, # Prefer aligning to nodes
                'OUTPUT': 'memory:lineas_snapped'
            })
            lineas_a_usar = res_snap['OUTPUT']
        except Exception as e:
            print(f"⚠️ Aviso en snap: {e}. Continuando directamente...")

    # 3. Poligonizar líneas (Line to Polygon)
    print("🔹 Paso 2/3: Poligonizando líneas en polígonos cerrados...")
    try:
        res_poly = processing.run("native:polygonize", {
            'INPUT': lineas_a_usar,
            'KEEP_FIELDS': False,
            'OUTPUT': 'memory:poligonos_generados'
        })
        capa_poligonos = res_poly['OUTPUT']
        cant_poligonos = capa_poligonos.featureCount()
        print(f"✅ Se formaron exitosamente {cant_poligonos} polígonos de predios.")
    except Exception as e:
        print(f"❌ Error al poligonizar: {e}")
        return

    # 4. Unión espacial (Spatial Join): Asignar el texto del punto que cae dentro del polígono
    print(f"🔹 Paso 3/3: Transfiriendo posesionarios (Spatial Join)...")
    
    # Verificar nombres de campos de la capa de puntos
    campos_puntos = [f.name() for f in capa_puntos.fields()]
    campo_encontrado = None
    
    # Buscar campo configurado o variantes comunes de CAD (case-insensitive)
    candidatos = [CAMPO_TEXTO_POSESIONARIO, "text", "TEXT", "STRING", "string", "Text", "nombre", "Nombre", "posesionario"]
    for c in candidatos:
        for f in campos_puntos:
            if f.lower() == c.lower():
                campo_encontrado = f
                break
        if campo_encontrado:
            break
            
    if campo_encontrado:
        print(f"📌 Usando el campo '{campo_encontrado}' como nombre del posesionario/texto.")
        campos_join = [campo_encontrado]
    else:
        print(f"ℹ️ Campos detectados en puntos: {campos_puntos}")
        print("ℹ️ Se transferirán todos los campos disponibles.")
        campos_join = campos_puntos

    salida = EXPORTAR_A_ARCHIVO if EXPORTAR_A_ARCHIVO else 'memory:Predios_con_Posesionarios'

    try:
        res_join = processing.run("native:joinattributesbylocation", {
            'INPUT': capa_poligonos,
            'JOIN': capa_puntos,
            'PREDICATE': [0, 5], # 0: intersecta, 5: contiene
            'JOIN_FIELDS': campos_join,
            'METHOD': 0, # 1 a 1: toma el posesionario contenido
            'DISCARD_NONMATCHING': False,
            'PREFIX': '',
            'OUTPUT': salida
        })
        
        capa_resultado = res_join['OUTPUT']
        
        if isinstance(capa_resultado, str):
            capa_final = QgsVectorLayer(capa_resultado, "Predios con Posesionarios", "ogr")
            project.addMapLayer(capa_final)
        else:
            capa_resultado.setName("Predios con Posesionarios")
            project.addMapLayer(capa_resultado)

        print("="*60)
        print("🎉 ¡PROCESO COMPLETADO CON ÉXITO!")
        print(f"✨ Capa agregada a QGIS: 'Predios con Posesionarios'")
        if EXPORTAR_A_ARCHIVO:
            print(f"📁 Guardado en disco: {EXPORTAR_A_ARCHIVO}")
        print("="*60)

    except Exception as e:
        print(f"❌ Error en la unión espacial: {e}")

# Ejecutar automáticamente al presionar Run
ejecutar_proceso()
