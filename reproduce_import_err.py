
import httpx
import sys
import csv

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "admin123"

def create_test_csv(filename):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["SKU", "Name", "Stock", "Category", "Location"])
        writer.writerow(["TEST-ERR-01", "Item", "10", "Genera", "Main"])

def run_error_test():
    print("Testing Error Conditions...")
    create_test_csv("test_err.csv")
    
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

        # 1. Test Missing File Key (Expect 422)
        print("\n--- Testing Wrong Key (Expect 422) ---")
        with open("test_err.csv", "rb") as f:
            files = {"wrong_key": ("test_err.csv", f, "text/csv")}
            resp = client.post(f"{BASE_URL}/inventory/import", headers=headers, files=files)
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")

        # 2. Test Trailing Slash (Expect 307)
        print("\n--- Testing Trailing Slash (Expect 307?) ---")
        with open("test_err.csv", "rb") as f:
            files = {"file": ("test_err.csv", f, "text/csv")}
            # Note: httpx follows redirects by default? No, usually false.
            resp = client.post(f"{BASE_URL}/inventory/import/", headers=headers, files=files)
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")

        # 3. Test Correct Request (Expect 200)
        print("\n--- Testing Correct Request (Expect 200) ---")
        with open("test_err.csv", "rb") as f:
            files = {"file": ("test_err.csv", f, "text/csv")}
            resp = client.post(f"{BASE_URL}/inventory/import", headers=headers, files=files)
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")

if __name__ == "__main__":
    run_error_test()
