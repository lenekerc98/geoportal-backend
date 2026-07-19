import urllib.request
import json
from app.core.database import SessionLocal
from app.core.security import create_access_token
from datetime import timedelta
from sqlalchemy import text

db = SessionLocal()
# Get a user
user = db.execute(text("SELECT id, username, rol, empresa_id FROM catastro.usuario LIMIT 1")).mappings().first()
if not user:
    print("No users found")
    exit()

token = create_access_token({
    "sub": user["username"],
    "id": user["id"],
    "role": user["rol"],
    "id_empresa": user["empresa_id"]
}, timedelta(minutes=10))

req = urllib.request.Request('http://127.0.0.1:8000/api/gis/predios', headers={'Authorization': 'Bearer ' + token})
try:
    res = urllib.request.urlopen(req)
    print("STATUS", res.getcode())
    print(res.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print(e.read().decode())
