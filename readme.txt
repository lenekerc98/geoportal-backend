En este archivo se encontrara configuracion sobre la base - api con qgis.

Para que funcione la conexión, debes ajustar los siguientes campos:

Anfitrión (Host):

Mueve el valor 192.168.100.24 (o escribe 127.0.0.1 si la base de datos está en tu misma máquina) al campo Anfitrión.
Deja el campo Servicio completamente vacío.
Base de datos:

Escribe catastro_db en este campo (actualmente está vacío).
Autenticación:

Haz clic en la pestaña Básica (al lado de Configuraciones).
Allí ingresa:
Usuario: postgres
Contraseña: L3n3k3rx98.
Detalles de la Base de Datos (Panel Derecho):

Marca la casilla Listar también tablas sin geometría (o Also list tables without geometry). Esto es muy importante para que QGIS pueda mostrarte las tablas roles y usuarios, ya que no contienen columnas de mapas/geometría.
Una vez hecho esto, haz clic en Probar conexión para verificar.

Luego se debe configurar pg_hba.conf
n tu instalación de Windows, el archivo pg_hba.conf se encuentra en la carpeta de datos de PostgreSQL, que está en la siguiente ruta:

📂 C:\Program Files\PostgreSQL\18\data\pg_hba.conf

¿Cómo modificarlo si quieres permitir la conexión desde la IP 192.168.100.24?
Abre tu editor de texto (como el Bloc de Notas) como Administrador:

Busca "Bloc de Notas" en el menú de inicio de Windows.
Haz clic derecho y selecciona Ejecutar como administrador.
Abre el archivo desde la ruta de arriba (asegúrate de cambiar el filtro de tipo de archivo de .txt a Todos los archivos (*.*) para poder verlo).
Agrega una línea al final del archivo: Para permitir que esa IP se conecte a cualquier base de datos con cualquier usuario, agrega la siguiente línea al final:


####SE AGREGA ESTO #####
text
host    all             all             192.168.100.24/32       scram-sha-256
(Si tienes problemas de autenticación, también puedes usar md5 o trust en lugar de scram-sha-256, pero scram-sha-256 es el estándar seguro por defecto en PostgreSQL 18).

Guarda el archivo.

Reinicia el servicio de PostgreSQL:

Abre el administrador de tareas de Windows o presiona Win + R, escribe services.msc y presiona Enter.
Busca el servicio postgresql-x64-18.
Haz clic derecho sobre él y selecciona Reiniciar.



Para que la base de datos pueda almacenar los datos espaciales (mapas, polígonos, puntos y linderos) y enviarlos al front-end, PostgreSQL necesita tener habilitada la extensión de PostGIS.

1. ¿Cómo habilitar PostGIS en tu PostgreSQL de Windows?
Como PostgreSQL 18 viene "vacío" de fábrica, debes instalar la extensión espacial PostGIS:

En el menú de inicio de Windows, busca y abre la herramienta Application Stack Builder (se instala junto con PostgreSQL).
Selecciona tu servidor de PostgreSQL y haz clic en Siguiente.
Despliega la categoría Spatial Extensions (Extensiones Espaciales) y marca la casilla de PostGIS (selecciona la versión más reciente compatible).
Dale a Siguiente para descargar e instalar PostGIS.
Una vez que termine la instalación, el backend (FastAPI) detectará PostGIS y se encargará de crear de forma automática el esquema catastro y todas las tablas espaciales (predio, vertice, linea_lindero, posesionario) y la vista v_predio_completo con sus respectivos permisos para tus usuarios.