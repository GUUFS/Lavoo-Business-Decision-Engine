import jwt
from datetime import datetime, timedelta

SECRET_KEY = "95946159b8ef6e99094215121ce02c7088fbc5db73b9a3b6764b74a45de09f8d"
ALGORITHM = "HS256"

payload = {
    "sub": "admin@gmail.com",
    "user_id": 6,
    "role": "admin",
    "exp": datetime.utcnow() + timedelta(hours=2)
}

token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(token)