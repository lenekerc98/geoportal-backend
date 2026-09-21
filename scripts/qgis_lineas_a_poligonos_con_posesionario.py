# -*- coding: utf-8 -*-
"""
========================================================================================
SISTEMA CATASTRO 2026 - HERRAMIENTA OFICIAL PARA QGIS
CONVERTIDOR DE LÍNEAS CAD A ESTRUCTURA COMPLETA (PREDIOS, VÉRTICES Y LINDEROS)
========================================================================================
Propósito:
  Transforma planos CAD/DWG/DXF o Shapefiles de líneas y textos en la estructura
  catastral oficial completa:
    1. Capa de PREDIOS (Polígonos): con posesionario, cédula, código, área en Ha y m².
    2. Capa de VÉRTICES (Puntos): numerados correlativamente (1, 2, 3...) con X e Y UTM.
    3. Capa de LINDEROS (Líneas): con tramos (1-2, 2-3...), longitud en metros y rumbo topográfico.

Compatible con: QGIS 3.x (Qt5) y QGIS 4.x (Qt6)
========================================================================================
"""

import os
import re
import math
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsWkbTypes,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsSingleSymbolRenderer,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsMarkerSymbol
)
from qgis.PyQt.QtCore import QVariant, Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDoubleSpinBox, QPushButton, QCheckBox, QFileDialog, 
    QMessageBox, QProgressBar, QGroupBox, QFormLayout
)
from qgis.PyQt.QtGui import QColor, QFont
import processing


def calcular_rumbo_topografico(p1, p2):
    """Calcula el rumbo topográfico estándar (ej: N 45° 30' 12" E) entre dos puntos UTM"""
    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    dist = math.hypot(dx, dy)
    if dist == 0:
        return "N 0° 0' 0\" E", 0.0

    angle_rad = math.atan2(dx, dy) # Azimut medido desde el Norte
    if angle_rad < 0:
        angle_rad += 2 * math.pi
    azimuth_deg = math.degrees(angle_rad)

    if 0 <= azimuth_deg <= 90:
        quadrant = 'NE'
        rumbo_deg = azimuth_deg
    elif 90 < azimuth_deg <= 180:
        quadrant = 'SE'
        rumbo_deg = 180 - azimuth_deg
    elif 180 < azimuth_deg <= 270:
        quadrant = 'SW'
        rumbo_deg = azimuth_deg - 180
    else:
        quadrant = 'NW'
        rumbo_deg = 360 - azimuth_deg

    d = int(rumbo_deg)
    m = int((rumbo_deg - d) * 60)
    s = round(((rumbo_deg - d) * 60 - m) * 60)
    if s >= 60:
        s = 0
        m += 1
    if m >= 60:
        m = 0
        d += 1

    letra1 = 'N' if quadrant in ['NE', 'NW'] else 'S'
    letra2 = 'E' if quadrant in ['NE', 'SE'] else 'W'
    rumbo_str = f"{letra1} {d}° {m}' {s}\" {letra2}"
    return rumbo_str, round(dist, 2)


class DialogoPoligonizarCatastro(QDialog):
    def __init__(self, parent=None):
        super(DialogoPoligonizarCatastro, self).__init__(parent)
        self.setWindowTitle("Catastro 2026 | Generador de Predios, Vértices y Linderos")
        self.setMinimumWidth(560)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
                font-family: 'Segoe UI', Tahoma, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 14px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #0f172a;
            }
            QComboBox, QDoubleSpinBox {
                padding: 6px 10px;
                border: 1px solid #94a3b8;
                border-radius: 6px;
                background: #ffffff;
                font-size: 13px;
            }
            QComboBox:focus, QDoubleSpinBox:focus {
                border: 1.5px solid #0284c7;
            }
            QPushButton#btnEjecutar {
                background-color: #0284c7;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton#btnEjecutar:hover {
                background-color: #0369a1;
            }
            QPushButton#btnCancelar {
                background-color: #e2e8f0;
                color: #334155;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
            }
            QPushButton#btnCancelar:hover {
                background-color: #cbd5e1;
            }
        """)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Encabezado
        lbl_titulo = QLabel("🏛️ Estructuración Catastral Completa desde CAD")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #0369a1; margin-bottom: 2px;")
        layout.addWidget(lbl_titulo)

        lbl_sub = QLabel("Convierte líneas y textos en: 1) Predios, 2) Vértices topológicos y 3) Linderos con longitud y rumbo.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #64748b; margin-bottom: 8px;")
        layout.addWidget(lbl_sub)

        # Grupo 1: Capas de Entrada
        grp_capas = QGroupBox("1. Selección de Capas de Entrada")
        form_capas = QFormLayout()
        grp_capas.setLayout(form_capas)

        self.cb_lineas = QComboBox()
        self.cb_puntos = QComboBox()
        self.cb_campo = QComboBox()

        form_capas.addRow("Capa de Líneas (Bordes/Linderos):", self.cb_lineas)
        form_capas.addRow("Capa de Puntos (Nombres/Posesionarios):", self.cb_puntos)
        form_capas.addRow("Campo del Texto / Nombre:", self.cb_campo)

        self.cb_puntos.currentIndexChanged.connect(self.actualizar_campos_texto)
        layout.addWidget(grp_capas)

        # Grupo 2: Opciones de Estructuración
        grp_params = QGroupBox("2. Opciones y Tolerancia Topológica")
        form_params = QFormLayout()
        grp_params.setLayout(form_params)

        self.sp_snap = QDoubleSpinBox()
        self.sp_snap.setRange(0.0, 5.0)
        self.sp_snap.setSingleStep(0.01)
        self.sp_snap.setValue(0.08) # 8 cm por defecto para tolerar CAD
        self.sp_snap.setSuffix(" m")
        self.sp_snap.setToolTip("Une vértices cercanos que no se tocan exactamente en el plano CAD.")

        self.chk_gen_vertices = QCheckBox("Generar capa de VÉRTICES (Puntos correlativos 1, 2, 3...)")
        self.chk_gen_vertices.setChecked(True)

        self.chk_gen_linderos = QCheckBox("Generar capa de LINDEROS (Líneas con longitud en metros y rumbo)")
        self.chk_gen_linderos.setChecked(True)

        self.chk_etiquetar = QCheckBox("Etiquetar automáticamente en QGIS con estilos profesionales")
        self.chk_etiquetar.setChecked(True)

        form_params.addRow("Tolerancia de Cierre (Snap):", self.sp_snap)
        form_params.addRow("", self.chk_gen_vertices)
        form_params.addRow("", self.chk_gen_linderos)
        form_params.addRow("", self.chk_etiquetar)
        layout.addWidget(grp_params)

        # Barra de progreso
        self.progreso = QProgressBar()
        self.progreso.setTextVisible(False)
        self.progreso.setFixedHeight(8)
        self.progreso.hide()
        layout.addWidget(self.progreso)

        # Botones de Acción
        h_botones = QHBoxLayout()
        h_botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnCancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        h_botones.addWidget(self.btn_cancelar)

        self.btn_ejecutar = QPushButton("⚡ Generar Estructura Catastral")
        self.btn_ejecutar.setObjectName("btnEjecutar")
        self.btn_ejecutar.clicked.connect(self.ejecutar)
        h_botones.addWidget(self.btn_ejecutar)

        layout.addLayout(h_botones)

        self.cargar_capas_proyecto()

    def cargar_capas_proyecto(self):
        project = QgsProject.instance()
        capas = project.mapLayers().values()

        self.cb_lineas.clear()
        self.cb_puntos.clear()

        for lyr in capas:
            if not isinstance(lyr, QgsVectorLayer) or not lyr.isValid():
                continue
            geom_type = lyr.geometryType()
            if geom_type == QgsWkbTypes.LineGeometry:
                self.cb_lineas.addItem(f"{lyr.name()} ({lyr.featureCount()} entidades)", lyr)
            elif geom_type == QgsWkbTypes.PointGeometry:
                self.cb_puntos.addItem(f"{lyr.name()} ({lyr.featureCount()} entidades)", lyr)

        if self.cb_lineas.count() == 0:
            self.cb_lineas.addItem("⚠️ No hay capas de líneas en el proyecto", None)
            self.btn_ejecutar.setEnabled(False)
        if self.cb_puntos.count() == 0:
            self.cb_puntos.addItem("⚠️ No hay capas de puntos en el proyecto", None)
            self.btn_ejecutar.setEnabled(False)

        self.actualizar_campos_texto()

    def actualizar_campos_texto(self):
        lyr_puntos = self.cb_puntos.currentData()
        self.cb_campo.clear()
        if not lyr_puntos:
            return

        campos = [f.name() for f in lyr_puntos.fields()]
        seleccionado_idx = 0
        prioridades = ['text', 'string', 'texto', 'nombre', 'posesionario', 'propietario', 'codigo', 'cod_catastral']
        for i, c in enumerate(campos):
            self.cb_campo.addItem(c)
            for prio in prioridades:
                if prio in c.lower():
                    seleccionado_idx = i
                    break

        if self.cb_campo.count() > 0:
            self.cb_campo.setCurrentIndex(seleccionado_idx)

    def ejecutar(self):
        lyr_lineas = self.cb_lineas.currentData()
        lyr_puntos = self.cb_puntos.currentData()
        campo_texto = self.cb_campo.currentText()
        snap_tol = self.sp_snap.value()

        if not lyr_lineas or not lyr_puntos or not campo_texto:
            QMessageBox.warning(self, "Campos Incompletos", "Selecciona las capas de líneas, puntos y el campo de texto.")
            return

        self.btn_ejecutar.setEnabled(False)
        self.progreso.show()
        self.progreso.setValue(10)

        try:
            lineas_a_usar = lyr_lineas
            project = QgsProject.instance()

            # 1. Snap si se solicita
            if snap_tol > 0:
                self.progreso.setValue(20)
                try:
                    res_snap = processing.run("native:snapgeometries", {
                        'INPUT': lyr_lineas,
                        'REFERENCE_LAYER': lyr_lineas,
                        'TOLERANCE': snap_tol,
                        'BEHAVIOR': 0,
                        'OUTPUT': 'memory:lineas_snapped'
                    })
                    lineas_a_usar = res_snap['OUTPUT']
                except Exception:
                    pass

            # 2. Partir líneas en todas las intersecciones (Nodulación topológica)
            self.progreso.setValue(35)
            try:
                # Disolver líneas y nodularlas
                res_lines_clean = processing.run("native:splitlinesbylayer", {
                    'INPUT': lineas_a_usar,
                    'LINES': lineas_a_usar,
                    'OUTPUT': 'memory:lineas_noduladas'
                })
                lineas_poligonizar = res_lines_clean['OUTPUT']
            except Exception:
                lineas_poligonizar = lineas_a_usar

            # 3. Poligonizar
            self.progreso.setValue(50)
            res_poly = processing.run("native:polygonize", {
                'INPUT': lineas_poligonizar,
                'KEEP_FIELDS': False,
                'OUTPUT': 'memory:poligonos_catastro'
            })
            capa_poligonos = res_poly['OUTPUT']
            total_predios = capa_poligonos.featureCount()

            if total_predios == 0:
                QMessageBox.critical(self, "Sin Polígonos", "No se formaron polígonos cerrados. Prueba incrementando la tolerancia de Snap.")
                self.progreso.hide()
                self.btn_ejecutar.setEnabled(True)
                return

            # 4. Crear capas de salida en memoria con la estructura Catastro 2026
            crs_auth = lyr_lineas.crs().authid()
            
            # 4.1 Capa Predios
            capa_predios = QgsVectorLayer(f"Polygon?crs={crs_auth}", f"Predios Catastro ({total_predios})", "memory")
            prov_predios = capa_predios.dataProvider()
            prov_predios.addAttributes([
                QgsField("cod_catastral", QVariant.String, len=50),
                QgsField("nombre_posesionario", QVariant.String, len=150),
                QgsField("cedula", QVariant.String, len=20),
                QgsField("area_ha", QVariant.Double, prec=4),
                QgsField("area_m2", QVariant.Double, prec=2),
                QgsField("area_plano", QVariant.String, len=50),
                QgsField("estado_plano", QVariant.String, len=50)
            ])
            capa_predios.updateFields()

            # 4.2 Capa Vértices
            capa_vertices = None
            if self.chk_gen_vertices.isChecked():
                capa_vertices = QgsVectorLayer(f"Point?crs={crs_auth}", "Vértices Catastro", "memory")
                prov_vert = capa_vertices.dataProvider()
                prov_vert.addAttributes([
                    QgsField("cod_catastral", QVariant.String, len=50),
                    QgsField("codigo", QVariant.String, len=20),
                    QgsField("coord_x", QVariant.Double, prec=2),
                    QgsField("coord_y", QVariant.Double, prec=2)
                ])
                capa_vertices.updateFields()

            # 4.3 Capa Linderos
            capa_linderos = None
            if self.chk_gen_linderos.isChecked():
                capa_linderos = QgsVectorLayer(f"LineString?crs={crs_auth}", "Linderos Catastro", "memory")
                prov_lind = capa_linderos.dataProvider()
                prov_lind.addAttributes([
                    QgsField("cod_catastral", QVariant.String, len=50),
                    QgsField("tramo", QVariant.String, len=30),
                    QgsField("longitud", QVariant.Double, prec=2),
                    QgsField("rumbo", QVariant.String, len=50),
                    QgsField("colindante", QVariant.String, len=150)
                ])
                capa_linderos.updateFields()

            # Indexar puntos para búsqueda espacial rápida
            from qgis.core import QgsSpatialIndex
            sp_index_puntos = QgsSpatialIndex(lyr_puntos.getFeatures())
            feats_puntos_dict = {f.id(): f for f in lyr_puntos.getFeatures()}

            self.progreso.setValue(70)

            feats_predios = []
            feats_vertices = []
            feats_linderos = []

            for i, poly_feat in enumerate(capa_poligonos.getFeatures()):
                poly_geom = poly_feat.geometry()
                if not poly_geom or poly_geom.isEmpty():
                    continue

                area_m2 = poly_geom.area()
                area_ha = round(area_m2 / 10000.0, 4)

                # Descartar micro-polígonos parásitos (menores a 1 m²)
                if area_m2 < 1.0:
                    continue

                # Código catastral correlativo
                cod_catastral = f"PRED-{i+1:04d}"

                # Buscar puntos que caen dentro del predio
                candidate_ids = sp_index_puntos.intersects(poly_geom.boundingBox())
                puntos_dentro = []
                for cid in candidate_ids:
                    pt_feat = feats_puntos_dict.get(cid)
                    if pt_feat and poly_geom.contains(pt_feat.geometry()):
                        val_txt = str(pt_feat[campo_texto] or "").strip()
                        if val_txt:
                            puntos_dentro.append(val_txt)

                # Parser inteligente de los textos CAD agrupados
                nombre_pos = "SIN ASIGNAR"
                cedula_val = ""
                area_plano_val = ""
                estado_val = ""

                for txt in puntos_dentro:
                    # 1. Buscar Cédula (C.C. o 10 dígitos)
                    m_ced = re.search(r'(?:C\.?C\.?|CEDULA|CI)?\s*(\d{10})', txt, re.IGNORECASE)
                    if m_ced:
                        cedula_val = m_ced.group(1)
                        continue

                    # 2. Buscar Área declarada en plano
                    if re.search(r'ÁREA|AREA|HAS|HA', txt, re.IGNORECASE) and re.search(r'\d', txt):
                        area_plano_val = txt
                        continue

                    # 3. Buscar Estado / Aprobación
                    if re.search(r'APROBADO|NOVIEMBRE|OCTUBRE|DICIEMBRE|ENERO|FEBRERO|MARZO|2019|2020|2021|2022|2023|2024|2025|2026', txt, re.IGNORECASE):
                        if not estado_val:
                            estado_val = txt
                        continue

                    # 4. Descartar textos de carreteras o notas secundarias
                    if re.search(r'CARRETERO|VIA|CAMINO|ESTERO|RIO|CANAL', txt, re.IGNORECASE):
                        continue

                    # 5. Si tiene letras y parece nombre de persona (2 o más palabras)
                    if nombre_pos == "SIN ASIGNAR" and len(txt.split()) >= 2:
                        nombre_pos = txt

                # Si aún no se asignó nombre pero hay algún texto
                if nombre_pos == "SIN ASIGNAR" and puntos_dentro:
                    for t in puntos_dentro:
                        if not re.search(r'C\.?C\.?|\d{10}|ÁREA|APROBADO', t, re.IGNORECASE):
                            nombre_pos = t
                            break

                # Crear feature del Predio
                fp = QgsFeature(capa_predios.fields())
                fp.setGeometry(poly_geom)
                fp.setAttributes([
                    cod_catastral,
                    nombre_pos,
                    cedula_val,
                    area_ha,
                    round(area_m2, 2),
                    area_plano_val,
                    estado_val
                ])
                feats_predios.append(fp)

                # Extraer Vértices y Linderos del anillo exterior
                try:
                    poly_pts = poly_geom.asPolygon()
                    if poly_pts and len(poly_pts) > 0:
                        ring = poly_pts[0]
                        num_verts = len(ring) - 1 # El último repite el primero
                        if num_verts >= 3:
                            # Vértices
                            if capa_vertices:
                                for v_idx in range(num_verts):
                                    pt = ring[v_idx]
                                    fv = QgsFeature(capa_vertices.fields())
                                    fv.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                                    fv.setAttributes([
                                        cod_catastral,
                                        f"{v_idx + 1}",
                                        round(pt.x(), 2),
                                        round(pt.y(), 2)
                                    ])
                                    feats_vertices.append(fv)

                            # Linderos
                            if capa_linderos:
                                for v_idx in range(num_verts):
                                    pt_ini = ring[v_idx]
                                    pt_fin = ring[(v_idx + 1) % num_verts]
                                    rumbo_txt, dist_m = calcular_rumbo_topografico(pt_ini, pt_fin)
                                    
                                    geom_line = QgsGeometry.fromPolylineXY([
                                        QgsPointXY(pt_ini.x(), pt_ini.y()),
                                        QgsPointXY(pt_fin.x(), pt_fin.y())
                                    ])

                                    fl = QgsFeature(capa_linderos.fields())
                                    fl.setGeometry(geom_line)
                                    fl.setAttributes([
                                        cod_catastral,
                                        f"{v_idx + 1}-{((v_idx + 1) % num_verts) + 1}",
                                        dist_m,
                                        rumbo_txt,
                                        "" # Colindante para edición posterior
                                    ])
                                    feats_linderos.append(fl)
                except Exception:
                    pass

            self.progreso.setValue(85)

            # Insertar entidades en capas
            prov_predios.addFeatures(feats_predios)
            capa_predios.updateExtents()

            if capa_vertices:
                prov_vert.addFeatures(feats_vertices)
                capa_vertices.updateExtents()

            if capa_linderos:
                prov_lind.addFeatures(feats_linderos)
                capa_linderos.updateExtents()

            # Estilos y Simbología Profesional Catastral
            if self.chk_etiquetar.isChecked():
                # 1. Simbología y Etiquetas de Predios
                simb_poly = QgsFillSymbol.createSimple({
                    'color': '14, 165, 233, 30',
                    'outline_color': '#0284c7',
                    'outline_width': '0.7',
                    'outline_style': 'solid'
                })
                capa_predios.setRenderer(QgsSingleSymbolRenderer(simb_poly))

                set_p = QgsPalLayerSettings()
                set_p.fieldName = """coalesce("nombre_posesionario", 'S/N') || '\n' || coalesce("cedula", '') || '\n' || format_number("area_ha", 4) || ' Ha'"""
                set_p.isExpression = True
                fmt_p = QgsTextFormat()
                fmt_p.setFont(QFont("Arial", 8, QFont.Bold))
                fmt_p.setColor(QColor("#0f172a"))
                buf_p = QgsTextBufferSettings()
                buf_p.setEnabled(True)
                buf_p.setSize(1.2)
                buf_p.setColor(QColor("#ffffff"))
                fmt_p.setBuffer(buf_p)
                set_p.setFormat(fmt_p)
                capa_predios.setLabeling(QgsVectorLayerSimpleLabeling(set_p))
                capa_predios.setLabelsEnabled(True)

                # 2. Simbología y Etiquetas de Vértices
                if capa_vertices:
                    simb_v = QgsMarkerSymbol.createSimple({
                        'name': 'circle',
                        'size': '2.5',
                        'color': '#ef4444',
                        'outline_color': '#ffffff',
                        'outline_width': '0.5'
                    })
                    capa_vertices.setRenderer(QgsSingleSymbolRenderer(simb_v))

                    set_v = QgsPalLayerSettings()
                    set_v.fieldName = '"codigo"'
                    fmt_v = QgsTextFormat()
                    fmt_v.setFont(QFont("Arial", 7, QFont.Bold))
                    fmt_v.setColor(QColor("#dc2626"))
                    buf_v = QgsTextBufferSettings()
                    buf_v.setEnabled(True)
                    buf_v.setSize(1.0)
                    buf_v.setColor(QColor("#ffffff"))
                    fmt_v.setBuffer(buf_v)
                    set_v.setFormat(fmt_v)
                    capa_vertices.setLabeling(QgsVectorLayerSimpleLabeling(set_v))
                    capa_vertices.setLabelsEnabled(True)

                # 3. Simbología y Etiquetas de Linderos
                if capa_linderos:
                    simb_l = QgsLineSymbol.createSimple({
                        'color': '#334155',
                        'width': '0.5',
                        'line_style': 'solid'
                    })
                    capa_linderos.setRenderer(QgsSingleSymbolRenderer(simb_l))

                    set_l = QgsPalLayerSettings()
                    set_l.fieldName = """format_number("longitud", 2) || 'm | ' || "rumbo" """
                    set_l.isExpression = True
                    fmt_l = QgsTextFormat()
                    fmt_l.setFont(QFont("Arial", 6, QFont.Normal))
                    fmt_l.setColor(QColor("#334155"))
                    buf_l = QgsTextBufferSettings()
                    buf_l.setEnabled(True)
                    buf_l.setSize(0.8)
                    buf_l.setColor(QColor("#ffffff"))
                    fmt_l.setBuffer(buf_l)
                    set_l.setFormat(fmt_l)
                    capa_linderos.setLabeling(QgsVectorLayerSimpleLabeling(set_l))
                    capa_linderos.setLabelsEnabled(True)

            # Añadir capas a QGIS en orden visual (Polígonos abajo, Líneas al medio, Puntos arriba)
            project.addMapLayer(capa_predios)
            if capa_linderos:
                project.addMapLayer(capa_linderos)
            if capa_vertices:
                project.addMapLayer(capa_vertices)

            self.progreso.setValue(100)
            con_pos = sum(1 for f in feats_predios if f["nombre_posesionario"] != "SIN ASIGNAR")

            QMessageBox.information(
                self,
                "¡Estructura Catastral Generada!",
                f"✅ PREDIOS CREADOS: {len(feats_predios)} polígonos.\n"
                f"👤 POSESIONARIOS ASIGNADOS: {con_pos} predios.\n"
                f"📍 VÉRTICES TOPOLÓGICOS: {len(feats_vertices)} puntos (1, 2, 3...).\n"
                f"📏 LINDEROS: {len(feats_linderos)} tramos con Longitud y Rumbo.\n\n"
                f"Las 3 capas han sido cargadas a QGIS con etiquetas y estilos completos."
            )
            self.accept()

        except Exception as err:
            QMessageBox.critical(self, "Error de Ejecución", f"Ocurrió un error:\n{str(err)}")
            self.progreso.hide()
            self.btn_ejecutar.setEnabled(True)


# =============================================================================
# INICIALIZADOR EN QGIS (Compatible con QGIS 3 / Qt5 y QGIS 4 / Qt6)
# =============================================================================
try:
    from qgis.utils import iface
    parent_window = iface.mainWindow() if iface else None
except Exception:
    parent_window = None

dlg = DialogoPoligonizarCatastro(parent=parent_window)
dlg.show()
if hasattr(dlg, 'exec'):
    dlg.exec()
elif hasattr(dlg, 'exec_'):
    dlg.exec_()
