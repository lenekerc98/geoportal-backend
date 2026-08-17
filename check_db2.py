from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv('c:\\LNCZ\\proyecto-catastro-2026\\backend\\.env')
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    res = conn.execute(text("SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_schema = 'catastro' AND table_name = 'codigo_catastral' AND column_name = 'fecha_creacion'")).fetchone()
    print("codigo_catastral:", res)
    
    res = conn.execute(text("SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_schema = 'catastro' AND table_name = 'predio' AND column_name = 'fecha_creacion'")).fetchone()
    print("predio:", res)
