import os
import sys

# Mock DATABASE_URL so database.py doesn't fail
os.environ["DATABASE_URL"] = "postgresql://dummy:dummy@localhost/dummy"

try:
    import app.main
    print("IMPORT SUCCESS!")
except Exception as e:
    import traceback
    traceback.print_exc()
