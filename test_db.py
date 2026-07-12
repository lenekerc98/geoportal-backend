import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("SELECT srid_lectura, srid_original, ST_AsText(bbox) FROM catastro.ortofotos_catalogo WHERE nombre_archivo = 'orto_chacarita.tif'")
print(cur.fetchone())
conn.close()
