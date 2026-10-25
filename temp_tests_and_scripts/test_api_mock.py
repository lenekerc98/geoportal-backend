from fastapi.testclient import TestClient
from app.main import app
from app.routers.users import get_current_user

class MockUser:
    id = 1
    role = "SuperAdmin"
    id_empresa = 1

def override_get_current_user():
    return MockUser()

app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)

res = client.get("/api/gis/predios")
print("STATUS:", res.status_code)
if res.status_code != 200:
    print(res.text)
else:
    print("SUCCESS")
