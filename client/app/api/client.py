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
            except Exception:
                pass
    
    def _save_tokens(self) -> None:
        """Save tokens to file."""
        try:
            data = {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
            }
            settings.TOKEN_FILE.write_text(json.dumps(data))
        except Exception:
            pass
    
    def _clear_tokens(self) -> None:
        """Clear saved tokens."""
        self._access_token = None
        self._refresh_token = None
        if settings.TOKEN_FILE.exists():
            settings.TOKEN_FILE.unlink()
    
    def set_tokens(self, access_token: str, refresh_token: str) -> None:
        """Set authentication tokens."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._save_tokens()
        
        # Update client headers
        if self._client:
            self._client.headers.update(self._get_headers())
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client has tokens."""
        return self._access_token is not None
    
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
            raise APIError(
                data.get("message", "Request failed"),
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
        """Get current user info."""
        return self.get("/auth/me")
    
    # ============== Inventory Methods ==============
    
    def get_items(
        self,
        location_id: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list:
        """Get inventory items."""
        params = {"skip": skip, "limit": limit}
        if location_id:
            params["location_id"] = location_id
        if search:
            params["search"] = search
        return self.get("/inventory/items", params)
    
    def get_item_by_barcode(self, barcode: str) -> Dict[str, Any]:
        """Get item by barcode."""
        return self.get(f"/inventory/items/barcode/{barcode}")
    
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
        return self.get("/customers", {"search": search})
    
    def get_customer_by_phone(self, phone: str) -> Dict[str, Any]:
        """Get customer by phone."""
        return self.get(f"/customers/phone/{phone}")
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


# Global client instance
api_client = APIClient()
