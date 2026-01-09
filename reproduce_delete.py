
import httpx
import sys
import uuid

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "admin123"

def run_test():
    print("Testing Item Deletion...")
    
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

        # 1. Create a dummy item to delete
        sku = f"DEL-TEST-{str(uuid.uuid4())[:8]}"
        item_data = {
            "sku": sku,
            "name": "Delete Me",
            "category_id": None, # Optional
            "location_id": None, # Will use default
            "current_stock": 10,
            "cost_price": 100,
            "selling_price": 200
        }
        
        # Need to get location/category first? 
        # API allows None for them? Let's check schemas or just try.
        # Looking at inventory.py, it requires valid UUIDs if provided, but let's try to get a location.
        loc_resp = client.get(f"{BASE_URL}/locations", headers=headers)
        if loc_resp.status_code == 200 and loc_resp.json():
            item_data["location_id"] = loc_resp.json()[0]["id"]
            
        print(f"Creating item {sku}...")
        resp = client.post(f"{BASE_URL}/inventory/items", json=item_data, headers=headers)
        if resp.status_code != 201:
            print(f"Failed to create item: {resp.text}")
            return
        
        item_id = resp.json()["id"]
        print(f"Item created: {item_id}")

        # 2. Delete the item
        print(f"Deleting item {item_id}...")
        # Note: inventory.py route is DELETE /items/{item_id}
        resp = client.delete(f"{BASE_URL}/inventory/items/{item_id}", headers=headers)
        print(f"Delete Status: {resp.status_code}")
        
        if resp.status_code == 204:
            print("Delete successful (204 No Content)")
        else:
            print(f"Delete failed: {resp.text}")

        # 3. Verify it's gone from list
        print("Verifying item is gone...")
        resp = client.get(f"{BASE_URL}/inventory/items?search={sku}", headers=headers)
        items = resp.json()
        if not items:
            print("Item not found in list (Correct).")
        else:
            print(f"Item STILL found in list: {items}")

if __name__ == "__main__":
    run_test()
