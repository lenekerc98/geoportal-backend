import sys
import os
sys.path.append('C:\\LNCZ\\proyecto-catastro-2026\\backend')
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('C:\\LNCZ\\proyecto-catastro-2026\\backend\\.env')
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    res = conn.execute(text("SELECT id, codigo_catastral, ST_AsText(geom) FROM catastro.predios WHERE codigo_catastral IN ('010101006', '010101011')")).fetchall()
    print(res)
