import os
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
    QgsProcessingParameterRasterDestination
)
from osgeo import gdal, osr
import psycopg2

class CatalogarOrtofotos(QgsProcessingAlgorithm):
    DIR_ORTOFOTOS = 'DIR_ORTOFOTOS'
    OUTPUT_VRT = 'OUTPUT_VRT'
    DB_HOST = 'DB_HOST'
    DB_PORT = 'DB_PORT'
    DB_NAME = 'DB_NAME'
    DB_USER = 'DB_USER'
    DB_PASS = 'DB_PASS'
    
    SRID_DESTINO = 32717  # WGS 84 / UTM zone 17S (Catastro 2026)

    def initAlgorithm(self, config=None):
        # Parámetro para seleccionar la carpeta de las ortofotos
        self.addParameter(
            QgsProcessingParameterFile(
                self.DIR_ORTOFOTOS,
                'Carpeta de las Ortofotos (Origen)',
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=r'D:\_Ortofotos\NuevaVentanas'
            )
        )
        
        # Parámetro nativo de destino ráster de QGIS
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT_VRT,
                'Guardar Mosaico Virtual (.vrt)',
                defaultValue=r'C:\LNCZ\proyecto-catastro-2026\backend\ortofotos.vrt'
            )
        )
        
        # Parámetros de la base de datos
        self.addParameter(
            QgsProcessingParameterString(
                self.DB_HOST,
                'Host de la Base de Datos',
                defaultValue='localhost'
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DB_PORT,
                'Puerto de la Base de Datos',
                defaultValue='5432'
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DB_NAME,
                'Nombre de la Base de Datos',
                defaultValue='catastro_db'
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DB_USER,
                'Usuario de la Base de Datos',
                defaultValue='postgres'
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DB_PASS,
                'Contraseña de la Base de Datos',
                defaultValue='L3n3k3rx98.'
            )
        )

    def obtener_datos_ortofoto(self, ruta_archivo, feedback):
        """Usa GDAL para obtener los límites de la imagen y su SRID."""
        gdal.UseExceptions()
        try:
            ds = gdal.Open(ruta_archivo)
            width = ds.RasterXSize
            height = ds.RasterYSize
            gt = ds.GetGeoTransform()
            
            xmin = gt[0]
            ymax = gt[3]
            xmax = xmin + width * gt[1] + height * gt[2]
            ymin = ymax + width * gt[4] + height * gt[5]
            
            proj = ds.GetProjection()
            srs = osr.SpatialReference()
            srs.ImportFromWkt(proj)
            
            srs.AutoIdentifyEPSG()
            epsg_code = srs.GetAuthorityCode(None)
            srid = int(epsg_code) if epsg_code else None
            
            wkt_geom = f"POLYGON(({xmin} {ymin}, {xmin} {ymax}, {xmax} {ymax}, {xmax} {ymin}, {xmin} {ymin}))"
            
            return wkt_geom, srid
        except Exception as e:
            feedback.reportError(f"Error al leer metadatos de {os.path.basename(ruta_archivo)}: {str(e)}")
            return None, None

    def processAlgorithm(self, parameters, context, feedback):
        dir_ortofotos = self.parameterAsString(parameters, self.DIR_ORTOFOTOS, context)
        
        # Recuperar ruta de salida
        vrt_file = self.parameterAsString(parameters, self.OUTPUT_VRT, context)
        
        # Control estricto de tipo para evitar wrappers C++ no convertibles a string
        if not isinstance(vrt_file, str) or not vrt_file.strip() or vrt_file.lower() == 'none':
            raw_val = parameters.get(self.OUTPUT_VRT, '')
            if isinstance(raw_val, str) and raw_val.strip() != '':
                vrt_file = raw_val
            elif hasattr(raw_val, 'sink'):
                try:
                    sink_val = raw_val.sink()
                    if isinstance(sink_val, str) and sink_val.strip() != '':
                        vrt_file = sink_val
                except:
                    try:
                        sink_val = raw_val.sink
                        if isinstance(sink_val, str) and sink_val.strip() != '':
                            vrt_file = sink_val
                    except:
                        pass
            
        # Fallback definitivo si sigue sin ser un string válido
        if not isinstance(vrt_file, str) or not vrt_file.strip():
            vrt_file = r'C:\LNCZ\proyecto-catastro-2026\backend\ortofotos.vrt'
            
        db_host = self.parameterAsString(parameters, self.DB_HOST, context)
        db_port = self.parameterAsString(parameters, self.DB_PORT, context)
        db_name = self.parameterAsString(parameters, self.DB_NAME, context)
        db_user = self.parameterAsString(parameters, self.DB_USER, context)
        db_pass = self.parameterAsString(parameters, self.DB_PASS, context)
        
        if not os.path.exists(dir_ortofotos):
            feedback.reportError(f"Error: La ruta de las ortofotos no existe: {dir_ortofotos}")
            return {}
            
        feedback.pushInfo(f"Escaneando carpeta: {dir_ortofotos}...")
        archivos = [f for f in os.listdir(dir_ortofotos) if f.lower().endswith(('.tif', '.tiff', '.ecw', '.jp2'))]
        feedback.pushInfo(f"Se encontraron {len(archivos)} archivos ráster compatibles.")
        
        if not archivos:
            feedback.pushInfo("No hay archivos ráster para procesar.")
            return {}
            
        # 1. Crear el mosaico virtual VRT de las imágenes
        feedback.pushInfo("Generando Mosaico Virtual (VRT)...")
        rutas_completas = [os.path.join(dir_ortofotos, f) for f in archivos]
        try:
            gdal.UseExceptions()
            vrt_options = gdal.BuildVRTOptions(resampleAlg='near', addAlpha=True)
            vrt_ds = gdal.BuildVRT(vrt_file, rutas_completas, options=vrt_options)
            
            # Construir pirámides automáticamente para navegación ultrarrápida (estilo Google Maps)
            feedback.pushInfo("Construyendo pirámides (overviews) para navegación rápida...")
            vrt_ds.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32, 64])
            
            vrt_ds = None  # Cierra y escribe el archivo VRT y su respectivo .vrt.ovr
            feedback.pushInfo(f"Mosaico VRT guardado con éxito en: {vrt_file}")
            
            # Cargar automáticamente la capa en el lienzo de QGIS de forma segura (hilo principal)
            from qgis.PyQt.QtCore import QTimer
            def cargar_vrt_seguro():
                from qgis.core import QgsProject, QgsRasterLayer
                proyecto = QgsProject.instance()
                # Eliminar capa existente si la hay
                existentes = proyecto.mapLayersByName("Mosaico Ortofotos")
                for c in existentes:
                    proyecto.removeMapLayer(c)
                # Agregar la nueva capa ráster
                rlayer = QgsRasterLayer(vrt_file, "Mosaico Ortofotos")
                if rlayer.isValid():
                    proyecto.addMapLayer(rlayer)
            
            QTimer.singleShot(200, cargar_vrt_seguro)
            
        except Exception as vrt_err:
            feedback.reportError(f"Error al generar el Mosaico VRT: {str(vrt_err)}")
            return {}
            
        # 2. Conectar a PostgreSQL (Catalogado en base de datos en segundo plano)
        feedback.pushInfo("Catalogando en PostgreSQL en segundo plano...")
        try:
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_pass
            )
            cursor = conn.cursor()
        except Exception as conn_err:
            feedback.reportError(f"Error al conectar a PostgreSQL: {str(conn_err)}")
            return {self.OUTPUT_VRT: vrt_file}
            
        try:
            # Crear la tabla si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS catastro.ortofotos_catalogo (
                    id SERIAL PRIMARY KEY,
                    nombre_archivo VARCHAR(255) UNIQUE NOT NULL,
                    ruta_completa VARCHAR(1024) NOT NULL,
                    srid_original INT,
                    geom geometry(Polygon, 32717)
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ortofotos_catalogo_geom ON catastro.ortofotos_catalogo USING gist(geom);")
            conn.commit()
            
            insertados = 0
            actualizados = 0
            
            total = len(archivos)
            for i, f in enumerate(archivos):
                if feedback.isCanceled():
                    feedback.pushInfo("Operación cancelada por el usuario.")
                    break
                    
                ruta_completa = os.path.join(dir_ortofotos, f)
                wkt_geom, srid_orig = self.obtener_datos_ortofoto(ruta_completa, feedback)
                
                if not wkt_geom:
                    continue
                    
                srid_lectura = srid_orig if srid_orig else self.SRID_DESTINO
                
                try:
                    cursor.execute(
                        "SELECT id FROM catastro.ortofotos_catalogo WHERE nombre_archivo = %s", 
                        (f,)
                    )
                    exists = cursor.fetchone()
                    
                    if exists:
                        cursor.execute("""
                            UPDATE catastro.ortofotos_catalogo
                            SET ruta_completa = %s,
                                srid_original = %s,
                                geom = ST_Transform(ST_GeomFromText(%s, %s), %s)
                            WHERE nombre_archivo = %s
                        """, (ruta_completa, srid_orig, wkt_geom, srid_lectura, self.SRID_DESTINO, f))
                        actualizados += 1
                    else:
                        cursor.execute("""
                            INSERT INTO catastro.ortofotos_catalogo (nombre_archivo, ruta_completa, srid_original, geom)
                            VALUES (%s, %s, %s, ST_Transform(ST_GeomFromText(%s, %s), %s))
                        """, (f, ruta_completa, srid_orig, wkt_geom, srid_lectura, self.SRID_DESTINO))
                        insertados += 1
                    
                    feedback.setProgress(int((i + 1) / total * 100))
                except Exception as insert_err:
                    feedback.reportError(f"Error al insertar en DB {f}: {str(insert_err)}")
                    conn.rollback()
                    continue
            
            conn.commit()
            feedback.pushInfo("\n--- PROCESO COMPLETADO ---")
            feedback.pushInfo(f"Ortofotos insertadas en DB: {insertados}")
            feedback.pushInfo(f"Ortofotos actualizadas en DB: {actualizados}")
            
        except Exception as e:
            feedback.reportError(f"Error general en el proceso de DB: {str(e)}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
            
        # Retornamos el archivo VRT para que QGIS lo cargue automáticamente de forma nativa y segura
        return {self.OUTPUT_VRT: vrt_file}

    def name(self):
        return 'catalogarortofotos'

    def displayName(self):
        return 'Catalogar Ortofotos en DB'

    def group(self):
        return 'Catastro'

    def groupId(self):
        return 'catastro'

    def createInstance(self):
        return CatalogarOrtofotos()
