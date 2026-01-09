
import httpx
import sys

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "admin123"

def run_test():
    print("Testing Purchase Order List...")
    
    with httpx.Client(timeout=10.0) as client:
        # Login
        try:
            resp = client.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
            if resp.status_code != 200:
                print(f"Login failed: {resp.text}")
                return
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
        except Exception as e:
            print(f"Connection failed: {e}")
            return

        # Get POs
        print("Fetching POs...")
        resp = client.get(f"{BASE_URL}/purchase-orders/", headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

if __name__ == "__main__":
    run_test()
