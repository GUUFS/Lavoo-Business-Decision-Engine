import requests
import sys

BASE_URL = "http://localhost:8000"

def test_flow():
    # 1. Login
    print("--- 1. Logging in ---")
    try:
        login_res = requests.post(
            f"{BASE_URL}/api/login",
            json={"email": "admin@gmail.com", "password": "admin123"}
        )
        print(f"Login Status: {login_res.status_code}")
        if login_res.status_code != 200:
            print(f"Login Failed: {login_res.text}")
            return
        
        token = login_res.json().get("access_token")
        print(f"Got Token: {token[:20]}...")
    except Exception as e:
        print(f"Login Error: {e}")
        return

    # 2. Run Scan
    print("\n--- 2. Running Full Scan ---")
    try:
        scan_res = requests.post(
            f"{BASE_URL}/api/security/scan/full",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Scan Status: {scan_res.status_code}")
        print(f"Scan Response: {scan_res.text}")
    except Exception as e:
        print(f"Scan Error: {e}")

if __name__ == "__main__":
    test_flow()
