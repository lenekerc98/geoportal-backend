import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

sql = """
UPDATE catastro.linea_lindero
SET rumbo = catastro.calcular_rumbo(ST_StartPoint(geom), ST_EndPoint(geom))
WHERE rumbo IS NULL AND geom IS NOT NULL;
"""

try:
    with engine.begin() as conn:
        result = conn.execute(text(sql))
        print(f"Updated {result.rowcount} linderos with calculated rumbo!")
except Exception as e:
    print("Error:", e)
