from app.core.database import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
query = text('''
    SELECT ST_AsGeoJSON(ST_Transform(geom, 4326))::json
    FROM catastro.predio
    WHERE cod_catastral = '010101002'
''')

res = db.execute(query).scalar()
print("GEOM:", json.dumps(res))
