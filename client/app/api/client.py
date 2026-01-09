"""
API Client

HTTP client for communicating with the back office server.
"""

import json
from typing import Any, Dict, Optional
from pathlib import Path

import httpx

from app.config import settings


class APIError(Exception):
    """API Error with status code and details."""
    
    def __init__(self, message: str, status_code: int = 0, details: Any = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class APIClient:
    """
    HTTP client for server API communication.
    
    Handles authentication, token refresh, and request retries.
    """
    
    def __init__(self):
        self.base_url = settings.api_url.rstrip("/") + "/"
        self.timeout = settings.REQUEST_TIMEOUT
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._user_role: Optional[str] = None
        self._user_permissions: Dict[str, bool] = {}
        self._client: Optional[httpx.Client] = None
        
        # Load saved tokens
        self._load_tokens()
    
    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._get_headers(),
            )
        return self._client
    
    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers
    
    def _load_tokens(self) -> None:
        """Load tokens from file."""
        if settings.TOKEN_FILE.exists():
            try:
                data = json.loads(settings.TOKEN_FILE.read_text())
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                self._user_role = data.get("user_role")
                self._user_permissions = data.get("user_permissions", {})
            except Exception:
                pass
    
    def _save_tokens(self) -> None:
        """Save tokens to file."""
        try:
            data = {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "user_role": self._user_role,
                "user_permissions": self._user_permissions,
            }
            settings.TOKEN_FILE.write_text(json.dumps(data))
        except Exception:
            pass
    
    def _clear_tokens(self) -> None:
        """Clear saved tokens."""
        self._access_token = None
        self._refresh_token = None
        self._user_role = None
        self._user_permissions = {}
        if settings.TOKEN_FILE.exists():
            settings.TOKEN_FILE.unlink()
    
    def set_tokens(self, access_token: str, refresh_token: str, user_role: Optional[str] = None, permissions: Optional[Dict] = None) -> None:
        """Set authentication tokens and user info."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        if user_role:
            self._user_role = user_role
        if permissions:
            self._user_permissions = permissions
        self._save_tokens()
        
        # Update client headers
        if self._client:
            self._client.headers.update(self._get_headers())
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client has tokens."""
        return self._access_token is not None
        
    @property
    def user_role(self) -> Optional[str]:
        """Get current user role."""
        return self._user_role

    def has_permission(self, permission: str) -> bool:
        """Check if user has a permission."""
        if self._user_role == "super_admin":
            return True
        
        # Check custom permissions
        if permission in self._user_permissions:
            return self._user_permissions[permission]
            
        # Default role-based permissions (simplified client-side mirror)
        role_permissions = {
            "admin": ["manage_users", "view_reports", "manage_inventory", "manage_sales"],
            "manager": ["view_reports", "manage_inventory", "manage_sales"],
            "cashier": ["manage_sales"],
            "inventory": ["manage_inventory"],
            "viewer": ["view_reports"],
        }
        return permission in role_permissions.get(self._user_role, [])
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response."""
        if response.status_code == 401:
            # Try to refresh token
            if self._refresh_token and "/auth/refresh" not in str(response.url):
                if self._try_refresh():
                    # Retry original request
                    return None  # Signal retry needed
            raise APIError("Unauthorized", 401)
        
        try:
            data = response.json()
        except Exception:
            data = {"message": response.text}
        
        if not response.is_success:
            # Handle Validation Errors (422)
            if response.status_code == 422 and isinstance(data.get("detail"), list):
                # Extract messages from detail list
                messages = []
                for err in data["detail"]:
                    loc = ".".join(str(l) for l in err.get("loc", []))
                    msg = err.get("msg", "Unknown error")
                    messages.append(f"{loc}: {msg}")
                message = "\n".join(messages)
            else:
                message = data.get("message", f"Request failed ({response.status_code})")

            raise APIError(
                message,
                response.status_code,
                data.get("details"),
            )
        
        return data
    
    def _try_refresh(self) -> bool:
        """Try to refresh access token."""
        try:
            response = self.client.post(
                "/auth/refresh",
                json={"refresh_token": self._refresh_token},
            )
            if response.is_success:
                data = response.json()
                self.set_tokens(data["access_token"], data["refresh_token"])
                return True
        except Exception:
            pass
        
        self._clear_tokens()
        return False
    
    def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        # Update headers
        self.client.headers.update(self._get_headers())
        
        # Ensure endpoint doesn't start with / to correctly join with base_url
        clean_endpoint = endpoint.lstrip("/")
        
        try:
            response = self.client.request(
                method,
                clean_endpoint,
                json=data,
                params=params,
            )
            
            result = self._handle_response(response)
            
            # Retry if needed (after token refresh)
            if result is None:
                response = self.client.request(
                    method,
                    endpoint,
                    json=data,
                    params=params,
                )
                result = self._handle_response(response)
            
            return result
            
        except httpx.ConnectError:
            raise APIError("Cannot connect to server", 0)
        except httpx.TimeoutException:
            raise APIError("Request timed out", 0)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request."""
        return self.request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """POST request."""
        return self.request("POST", endpoint, data=data)
    
    def patch(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """PATCH request."""
        return self.request("PATCH", endpoint, data=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request."""
        return self.request("DELETE", endpoint)
    
    def download_file(self, endpoint: str) -> bytes:
        """GET request for binary file download."""
        self.client.headers.update(self._get_headers())
        response = self.client.get(endpoint.lstrip("/"))
        if response.status_code == 200:
            return response.content
        raise APIError(f"Failed to download file: {response.text}", response.status_code)

    def upload_file(self, endpoint: str, file_path: str) -> Dict[str, Any]:
        """POST request with file upload."""
        headers = self._get_headers()
        del headers["Content-Type"] # httpx will set this for multipart
        
        with open(file_path, "rb") as f:
            files = {"file": (Path(file_path).name, f, "text/csv")}
            response = self.client.post(
                endpoint.lstrip("/"),
                headers=headers,
                files=files
            )
            return self._handle_response(response)
    
    # ============== Auth Methods ==============
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get tokens."""
        response = self.post("/auth/login", {
            "username": username,
            "password": password,
        })
        
        self.set_tokens(response["access_token"], response["refresh_token"])
        return response
    
    def logout(self) -> None:
        """Logout and clear tokens."""
        try:
            self.post("/auth/logout")
        except Exception:
            pass
        self._clear_tokens()
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get current user info and sync local state."""
        user = self.get("/auth/me")
        if user:
            self._user_role = user.get("role")
            self._user_permissions = user.get("permissions") or {}
            self._save_tokens()
        return user
    
    # ============== Inventory Methods ==============
    
    def get_items(
        self,
        location_id: Optional[str] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list:
        """Get inventory items."""
        params = {"skip": skip, "limit": limit}
        if location_id:
            params["location_id"] = location_id
        if category_id:
            params["category_id"] = category_id
        if search:
            params["search"] = search
        return self.get("/inventory/items", params)
    
    def get_low_stock_items(self, skip: int = 0, limit: int = 100) -> list:
        """Get items that are at or below reorder point."""
        return self.get("/inventory/items", {"is_low_stock": True, "skip": skip, "limit": limit})
    
    def get_item_by_barcode(self, barcode: str) -> Dict[str, Any]:
        """Get item by barcode."""
        return self.get(f"/inventory/items/barcode/{barcode}")
    
    def delete_item(self, item_id: str) -> Dict[str, Any]:
        """Delete an inventory item."""
        return self.delete(f"/inventory/items/{item_id}")
    
    def get_item_movements(self, item_id: str) -> list:
        """Get stock movement history for an item."""
        return self.get(f"/inventory/items/{item_id}/movements")
    
    def export_inventory(self, location_id: Optional[str] = None) -> bytes:
        """Export inventory CSV."""
        params = {}
        if location_id:
            params["location_id"] = location_id
        return self.download_file("/inventory/export")

    def get_import_template(self) -> bytes:
        """Download import template CSV."""
        return self.download_file("/inventory/import-template")

    def import_inventory(self, file_path: str) -> Dict[str, Any]:
        """Import inventory from CSV."""
        return self.upload_file("/inventory/import", file_path)

    def get_all_movements(self, skip: int = 0, limit: int = 50) -> list:
        """Get global stock movement audit log."""
        return self.get("/inventory/movements", {"skip": skip, "limit": limit})
    
    # ============== Supplier Methods ==============
    
    def get_suppliers(self, is_active: bool = True, search: Optional[str] = None) -> list:
        """Get all suppliers."""
        params = {"is_active": is_active}
        if search:
            params["search"] = search
        return self.get("/suppliers", params)
    
    def get_supplier(self, supplier_id: str) -> dict:
        """Get a single supplier."""
        return self.get(f"/suppliers/{supplier_id}")
    
    def create_supplier(self, supplier_data: dict) -> dict:
        """Create a new supplier."""
        return self.post("/suppliers", supplier_data)
    
    def update_supplier(self, supplier_id: str, supplier_data: dict) -> dict:
        """Update a supplier."""
        return self.patch(f"/suppliers/{supplier_id}", supplier_data)
    
    def delete_supplier(self, supplier_id: str) -> dict:
        """Deactivate a supplier (soft delete)."""
        return self.delete(f"/suppliers/{supplier_id}")
    
    # ============== Purchase Order Methods ==============
    
    def get_purchase_orders(self, supplier_id: Optional[str] = None, status: Optional[str] = None) -> list:
        """Get purchase orders."""
        params = {}
        if supplier_id:
            params["supplier_id"] = supplier_id
        if status:
            params["status"] = status
        return self.get("/purchase-orders/", params)
    
    def get_purchase_order(self, po_id: str) -> dict:
        """Get a single purchase order."""
        return self.get(f"/purchase-orders/{po_id}")
    
    def create_purchase_order(self, po_data: dict) -> dict:
        """Create a new purchase order."""
        return self.post("/purchase-orders/", po_data)
    
    def update_purchase_order(self, po_id: str, po_data: dict) -> dict:
        """Update a purchase order (status, notes, etc)."""
        return self.patch(f"/purchase-orders/{po_id}", po_data)
    
    def delete_purchase_order(self, po_id: str) -> dict:
        """Delete a purchase order."""
        return self.delete(f"/purchase-orders/{po_id}")
    
    def get_suggested_po_items(self, supplier_id: str) -> list:
        """Get suggested items to order for a supplier."""
        return self.get(f"/purchase-orders/suggest/{supplier_id}")
    
    # ============== Sales Methods ==============
    
    def create_sale(self, sale_data: Dict) -> Dict[str, Any]:
        """Create a new sale."""
        return self.post("/sales", sale_data)
    
    def get_sales(
        self,
        location_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list:
        """Get sales history."""
        params = {"skip": skip, "limit": limit}
        if location_id:
            params["location_id"] = location_id
        return self.get("/sales", params)
    
    # ============== Customer Methods ==============
    
    def search_customers(self, search: str) -> list:
        """Search customers."""
        return self.get("/customers/search", {"search": search})
    
    def get_customer_by_phone(self, phone: str) -> Dict[str, Any]:
        """Get customer by phone."""
        return self.get(f"/customers/phone/{phone}")
    
    # ============== Location Methods ==============
    
    def get_locations(self, is_active: Optional[bool] = None) -> list:
        """Get all locations."""
        params = {}
        if is_active is not None:
            params["is_active"] = is_active
        return self.get("/locations", params)
    
    def create_location(self, data: Dict) -> Dict[str, Any]:
        """Create a new location."""
        return self.post("/locations", data)
    
    def update_location(self, location_id: str, data: Dict) -> Dict[str, Any]:
        """Update a location."""
        return self.patch(f"/locations/{location_id}", data)
    
    def delete_location(self, location_id: str) -> Dict[str, Any]:
        """Delete a location."""
        return self.delete(f"/locations/{location_id}")
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


# Global client instance
api_client = APIClient()
