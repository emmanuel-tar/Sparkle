
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from app.api import api_client

def test_client_error_handling():
    print("Testing Client Error Handling...")
    
    # Login
    try:
        api_client.login("admin", "admin123")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # create dummy csv
    with open("test_err_client.csv", "w") as f:
        f.write("header\nval")

    # Manually trigger 422 by sending wrong key
    # We can't easily change key in api_client.import_inventory without hacking
    # But we can call upload_file's internal logic or mock
    
    # Let's verify by calling a non-existent endpoint or something that causes 422
    # The import endpoint requires a file. If we call it with wrong method? No.
    
    # Let's try to call `api_client.post` with bad data to a typed endpoint
    # E.g. create_category without name
    print("\n--- Testing Validation Error (422) ---")
    try:
        api_client.post("/inventory/categories", {"description": "Missing Name"})
        print("Success (Unexpected)")
    except Exception as e:
        print(f"Caught Exception: {e}")
        # Expected: "body.name: Field required" or similar

if __name__ == "__main__":
    test_client_error_handling()
