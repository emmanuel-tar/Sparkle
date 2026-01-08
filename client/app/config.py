"""
Client Configuration

Settings for the desktop client application.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# Load environment variables
load_dotenv()


@dataclass
class Settings:
    """Client application settings."""
    
    # Application
    APP_NAME: str = "RetailPro ERP"
    APP_VERSION: str = "1.0.0"
    
    # Server Connection
    SERVER_URL: str = os.getenv("SERVER_URL", "http://localhost:8000")
    API_BASE: str = "/api/v1"
    WS_URL: str = os.getenv("WS_URL", "ws://localhost:8000/ws")
    
    # Local Database
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
    DB_PATH: Path = DATA_DIR / "local_cache.db"
    
    # Authentication
    TOKEN_FILE: Path = DATA_DIR / ".token"
    
    # Connection Settings
    REQUEST_TIMEOUT: int = 30  # seconds
    CONNECTION_RETRY_DELAY: int = 5  # seconds
    MAX_RETRIES: int = 3
    
    # Sync Settings
    SYNC_INTERVAL: int = 60  # seconds
    OFFLINE_QUEUE_SIZE: int = 1000
    
    # POS Settings
    DEFAULT_TAX_RATE: float = 7.5
    CURRENCY: str = "NGN"
    CURRENCY_SYMBOL: str = "₦"
    
    # Hardware
    ENABLE_BARCODE_SCANNER: bool = True
    BARCODE_SCANNER_PORT: Optional[str] = None
    ENABLE_RECEIPT_PRINTER: bool = True
    RECEIPT_PRINTER_NAME: Optional[str] = None
    
    @property
    def api_url(self) -> str:
        """Full API URL."""
        return f"{self.SERVER_URL}{self.API_BASE}"
    
    def __post_init__(self):
        """Ensure directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
