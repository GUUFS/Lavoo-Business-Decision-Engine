import os
from sqlalchemy import create_url, create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found")
    exit(1)

engine = create_engine(db_url)
with engine.connect() as conn:
    result = conn.execute(text("SELECT email, is_admin FROM users WHERE email = 'admin@gmail.com'")).fetchone()
    if result:
        print(f"User: {result.email}, is_admin: {result.is_admin}")
    else:
        print("User admin@gmail.com not found")
