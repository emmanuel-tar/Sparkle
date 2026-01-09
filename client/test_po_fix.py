
import sys
import os

# Add current directory to path so imports work
sys.path.append(os.getcwd())

from app.api import api_client

def test_po_client():
    print("Testing APIClient PO Fix...")
    
    # Login first
    try:
        print("Logging in...")
        api_client.login("admin", "admin123")
        print("Login successful.")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # Test get_purchase_orders
    try:
        print("Calling get_purchase_orders()...")
        pos = api_client.get_purchase_orders()
        print(f"Success! Retrieved {len(pos)} POs.")
        print(pos)
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_po_client()
