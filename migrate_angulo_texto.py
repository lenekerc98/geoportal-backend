import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
db_url = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    cur.execute("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS angulo_texto NUMERIC(5,2) DEFAULT 0;")
    print("Columna angulo_texto añadida exitosamente a catastro.predio.")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
