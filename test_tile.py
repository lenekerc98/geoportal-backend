import os
from dotenv import load_dotenv

load_dotenv()

from app.routers.gis import generate_tile_bytes

source_file = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Complementos\Ortofoto_Completa.vrt"
print("Testing tile generation...")
# Tile: 14/4576/8256 (from the user's screenshot)
result = generate_tile_bytes(14, 4576, 8256, source_file)
if result is None:
    print("FAILED TO GENERATE TILE. RESULT IS NONE.")
else:
    print(f"SUCCESS! Tile generated, size: {len(result)} bytes.")
