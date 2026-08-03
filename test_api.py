import urllib.request
import json

try:
    req = urllib.request.Request('http://127.0.0.1:8000/api/proyectos')
    # Use the first user's token or just an empty one to see if we get a 403 or 500
    # Actually, we need a valid token to bypass Depends(get_current_user)
    # So I will just print what happens when we omit auth, it should be 401 Unauthorized.
    # If it's a 500 Internal Server Error before reaching auth, we'll see it.
    response = urllib.request.urlopen(req)
    print("Response:", response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode('utf-8'))
except Exception as e:
    print("Other Error:", e)
