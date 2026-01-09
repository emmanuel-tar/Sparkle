
import httpx
import sys
import csv
import io

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "admin123"

def create_test_csv(filename, encoding='utf-8', content=None):
    if content is None:
        content = [
            ["SKU", "Name", "Stock", "Category", "Location"],
            ["TEST-IMP-01", "Imported Item 1", "50", "General", "Main Store"]
        ]
    
    with open(filename, 'w', newline='', encoding=encoding) as f:
        writer = csv.writer(f)
        writer.writerows(content)
    print(f"Created {filename} with encoding {encoding}")

def run_import_test():
    print("Starting Import Verification...")
    
    with httpx.Client(timeout=10.0) as client:
        # 1. Login
        print("\nLogging in...")
        try:
            resp = client.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
            if resp.status_code != 200:
                print(f"Login failed: {resp.text}")
                return
            
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("Login successful.")
        except Exception as e:
            print(f"Connection failed: {e}")
            return

        # 2. Test UTF-8 Import
        print("\n--- Testing UTF-8 Import ---")
        create_test_csv("test_utf8.csv", encoding='utf-8')
        with open("test_utf8.csv", "rb") as f:
            files = {"file": ("test_utf8.csv", f, "text/csv")}
            resp = client.post(f"{BASE_URL}/inventory/import", headers=headers, files=files)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")

        # 3. Test Latin-1 Import (simulation of Excel/Windows CSV)
        print("\n--- Testing Latin-1 Import ---")
        # Add a special character that is different in utf-8 and latin-1
        content_latin = [
            ["SKU", "Name", "Stock", "Category", "Location"],
            ["TEST-IMP-02", "Café Item", "20", "General", "Main Store"]
        ]
        create_test_csv("test_latin1.csv", encoding='latin-1', content=content_latin)
        
        with open("test_latin1.csv", "rb") as f:
            files = {"file": ("test_latin1.csv", f, "text/csv")}
            resp = client.post(f"{BASE_URL}/inventory/import", headers=headers, files=files)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")

        # 4. Test Case Insensitive Headers
        print("\n--- Testing Case Insensitive Headers ---")
        content_case = [
            ["sku", "name", "stock", "category", "location"],
            ["TEST-IMP-03", "Lower Case Item", "30", "General", "Main Store"]
        ]
        create_test_csv("test_case.csv", encoding='utf-8', content=content_case)
        with open("test_case.csv", "rb") as f:
            files = {"file": ("test_case.csv", f, "text/csv")}
            resp = client.post(f"{BASE_URL}/inventory/import", headers=headers, files=files)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")

if __name__ == "__main__":
    run_import_test()
