import requests

login_data = {
    "username": "lcedeno",
    "password": "lenekerc98"
}
res = requests.post("http://127.0.0.1:8000/api/token", data=login_data)
if res.status_code != 200:
    print("Login failed:", res.status_code, res.text)
    exit(1)

token = res.json()["access_token"]
print("Logged in. Token:", token[:20] + "...")

res2 = requests.get("http://127.0.0.1:8000/api/proyectos", headers={"Authorization": f"Bearer {token}"})
print("Proyectos status:", res2.status_code)
try:
    print("Proyectos JSON:", res2.json())
except Exception as e:
    print("Proyectos raw:", res2.text)
