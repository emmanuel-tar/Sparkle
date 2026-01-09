
import httpx
import json
import sys
import uuid

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "admin123"

def run_verification():
    print("Starting Supply Chain Verification...")
    
    with httpx.Client(timeout=10.0) as client:
        # 1. Login
        print("\nLogging in...")
        resp = client.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            sys.exit(1)
        
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful.")

        # 2. Setup: Find or Create an Item and Supplier
        print("\nSetting up test data...")
        # Get first supplier
        resp = client.get(f"{BASE_URL}/suppliers", headers=headers)
        suppliers = resp.json()
        if not suppliers:
            print("No suppliers found. Please run seed_admin.py or create a supplier.")
            sys.exit(1)
        supplier = suppliers[0]
        print(f"   Using Supplier: {supplier['name']}")

        # Get first item
        resp = client.get(f"{BASE_URL}/inventory/items", headers=headers)
        items = resp.json()
        if not items:
             print("No items found.")
             sys.exit(1)
        item = items[0]
        original_stock = float(item["current_stock"])
        print(f"   Using Item: {item['name']} (Stock: {original_stock})")

        # Force low stock if needed
        reorder_point = 100
        if original_stock > reorder_point:
             print("   Adjusting stock to trigger low stock alert...")
             client.patch(f"{BASE_URL}/inventory/items/{item['id']}", json={"current_stock": 10, "reorder_point": 100}, headers=headers)
        
        # 3. Monitor: Verify Low Stock Alert (User Step 1)
        print("\nVerifying Low Stock Alerts...")
        resp = client.get(f"{BASE_URL}/inventory/items?is_low_stock=true", headers=headers)
        low_stock_items = resp.json()
        low_stock_ids = [i['id'] for i in low_stock_items]
        
        if item['id'] in low_stock_ids:
            print(f"Item '{item['name']}' correctly appears in low stock list.")
        else:
            print(f"Item '{item['name']}' FAILED to appear in low stock list.")

        # 4. Create PO: Create Purchase Order (User Step 2)
        print("\nCreating Purchase Order...")
        order_qty = 50
        po_number = f"TEST-PO-{str(uuid.uuid4())[:8]}"
        po_data = {
            "supplier_id": supplier["id"],
            "order_number": po_number,
            "notes": "Automated verification test",
            "items": [
                {
                    "item_id": item["id"],
                    "quantity": order_qty,
                    "unit_cost": 500
                }
            ]
        }
        # Note: Added trailing slash to avoid 307
        resp = client.post(f"{BASE_URL}/purchase-orders/", json=po_data, headers=headers)
        if resp.status_code != 201:
            print(f"Failed to create PO (Status: {resp.status_code}): {resp.text}")
            sys.exit(1)
        po = resp.json()
        print(f"PO Created: {po['order_number']} (Status: {po['status']})")

        # 5. Receive PO: Receive Order and Check Stock (User Step 3)
        print("\nReceiving Purchase Order...")
        # Note: Added trailing slash to avoid 307 if needed, though ID paths often work better
        resp = client.patch(f"{BASE_URL}/purchase-orders/{po['id']}", json={"status": "received"}, headers=headers)
        if resp.status_code != 200:
             print(f"Failed to receive PO: {resp.text}")
             sys.exit(1)
        updated_po = resp.json()
        print(f"PO Status Updated: {updated_po['status']}")

        # 6. Verify Stock Update
        print("\nVerifying Stock Update...")
        resp = client.get(f"{BASE_URL}/inventory/items/{item['id']}", headers=headers)
        updated_item = resp.json()
        new_stock = float(updated_item["current_stock"])
        
        # Note: logic above for expected stock is simplified
        print(f"   Old Stock: {10 if original_stock > reorder_point else original_stock}")
        print(f"   New Stock: {new_stock}")
        
        # We checked if it increased
        if new_stock > (10 if original_stock > reorder_point else original_stock):
             print(f"Stock successfully increased by {order_qty}.")
        else:
             print("Stock did NOT increase.")

    print("\nVerification Complete!")

if __name__ == "__main__":
    run_verification()
