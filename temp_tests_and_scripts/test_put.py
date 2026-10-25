import requests

# We don't have the token, so we can't test it directly unless we login.
# Let's login first.
url_login = "http://localhost:8000/api/token"
data = {"username": "lcedeno", "password": "lenekerc98"}
response = requests.post(url_login, data=data)
print("Login:", response.status_code, response.text)
if response.status_code == 200:
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try updating user 3
    url_put = "http://localhost:8000/api/users/3"
    payload = {"username": "lcedeno", "id_rol": 1}
    res = requests.put(url_put, json=payload, headers=headers)
    print("PUT:", res.status_code, res.text)
