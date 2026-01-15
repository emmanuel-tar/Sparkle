# RetailPro ERP - AI Coding Agent Instructions

## Architecture Overview

**RetailPro ERP** is a retail management system with **decoupled client-server architecture**:

- **Server**: FastAPI + PostgreSQL/SQLite + Redis, async-first with SQLAlchemy 2.0
- **Client**: PySide6 desktop app with local SQLite cache, communicates via HTTP/WebSocket

Key architectural decision: Clients are **offline-first** with background sync—they don't depend on server availability for basic operations.

## Critical Patterns

### 1. Server: Async SQLAlchemy Sessions

**Pattern**: Dependencies-based session management with FastAPI.

```python
# In app/api/deps.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
        await session.commit()

# In endpoints (always async!)
@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()
```

**Critical Rules**:
- All database operations use `await` - never block
- Use `Annotated[AsyncSession, Depends(get_db)]` in endpoint signatures
- Query pattern: `select(Model).where(...)` then `db.execute()` then `.scalar_one_or_none()` or `.scalars().all()`
- Always `await db.commit()` after mutations (automatic in deps)

### 2. Server: Models with Mixins

All models inherit from `Base` + mixins for common fields:

```python
# From app/models/base.py
class MyModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "my_models"
    
    field: Mapped[str] = mapped_column(String(100), unique=True)
    optional: Mapped[Optional[int]] = mapped_column(nullable=True)
    relationship: Mapped["OtherModel"] = relationship(...)
```

- **UUIDMixin**: Adds UUID primary key (compatible with SQLite via GUIDType)
- **TimestampMixin**: Adds `created_at`, `updated_at` (ALWAYS present)
- Use `Mapped[T]` type hints for column definitions
- JSON fields use `sqlalchemy.JSON` type

### 3. Server: Role-Based Access Control (RBAC)

Roles defined in `app/models/user.py`:
- `SUPER_ADMIN`: Full system access
- `ADMIN`: Location-level admin
- `MANAGER`: Reports access
- `CASHIER`: POS only
- `INVENTORY`: Inventory management
- `VIEWER`: Read-only

**Pattern**: Check user role in endpoint logic, not middleware. Use `get_current_user` dependency that validates JWT:

```python
from app.api.deps import CurrentUser

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: CurrentUser,  # Provides User object
    db: DBSession,
):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise ForbiddenException("Only super admins can delete users")
```

### 4. Client: Thread-Based Async Operations

Client uses **QThread** to prevent UI blocking on network calls:

```python
# Pattern from LoginThread
class MyThread(QThread):
    success = Signal(dict)  # Signal results back
    error = Signal(str)
    
    def run(self):
        try:
            result = api_client.do_something()
            self.success.emit(result)
        except APIError as e:
            self.error.emit(e.message)

# In View
thread = MyThread()
thread.success.connect(self._on_success)
thread.error.connect(self._on_error)
thread.start()
```

**Rule**: Never call HTTP directly in Qt event loop—always use QThread for I/O.

### 5. Client: Permission Checking

Views check permissions before enabling buttons:

```python
# From inventory_view.py
if not api_client.has_permission("manage_inventory"):
    self.add_btn.setEnabled(False)
    self.add_btn.setToolTip("You do not have permission...")
```

Permissions come from server JWT claims and cached in `api_client`.

## Development Workflows

### Start Server (Development)

```bash
cd server
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Option 1: SQLite (default, no Docker needed)
export USE_SQLITE=True  # or set in .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: PostgreSQL (requires docker-compose)
docker-compose up -d  # Starts Postgres + Redis
alembic upgrade head
uvicorn app.main:app --reload
```

### Start Client

```bash
cd client
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Important**: Client reads `SERVER_URL` from `.env` (defaults to `http://localhost:8000`).

### Database Migrations

Alembic manages schema. After model changes:

```bash
cd server
alembic revision --autogenerate -m "Add new field"
alembic upgrade head
```

### Testing

```bash
# Server
cd server
pytest tests/  # Uses pytest-asyncio

# Client
cd client
pytest tests/
```

## Common Tasks & Code Patterns

### Add a New Endpoint

1. Create model in `server/app/models/` (inherit from Base + mixins)
2. Create schema in `server/app/schemas/` (Pydantic model)
3. Add endpoint in `server/app/api/v1/{domain}.py`:
```python
@router.post("/items", response_model=ItemResponse)
async def create_item(
    request: ItemCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    db_item = Item(**request.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item
```

### Add a Client View

1. Create view in `client/app/ui/views/{domain}_view.py` (inherit from QWidget)
2. In `__init__`, call `_setup_ui()` then `_load_data()`
3. Use QThread for API calls:
```python
class MyView(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._load_data()
    
    def _load_data(self):
        thread = DataThread()
        thread.success.connect(self._on_data_loaded)
        thread.start()
```

### Connect Client to Server

```python
from app.api import api_client

# Make authenticated request
try:
    result = api_client.get("/items")  # Auto-adds Bearer token
except APIError as e:
    QMessageBox.warning(self, "Error", e.message)
```

## Key Files & Dependencies

| File | Purpose |
|------|---------|
| `server/app/config.py` | Settings (database, security, CORS) |
| `server/app/database.py` | SQLAlchemy async engine setup |
| `server/app/models/` | Database models (ORM) |
| `server/app/api/v1/` | Endpoint implementations |
| `server/app/core/security.py` | JWT, password hashing, auth |
| `client/app/api/client.py` | HTTP client wrapper (handles tokens) |
| `client/app/ui/views/` | Desktop views (PySide6 widgets) |

## External Dependencies

- **Server**: FastAPI, SQLAlchemy 2.0 (async), asyncpg (PostgreSQL), aiosqlite (SQLite), python-jose (JWT)
- **Client**: PySide6, httpx (HTTP), websockets, reportlab (PDF receipts)

## Configuration via Environment

Create `.env` files:

**Server** (`server/.env`):
```
USE_SQLITE=True  # False for PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_DB=retail_erp
DEBUG=True
```

**Client** (`client/.env`):
```
SERVER_URL=http://localhost:8000
CURRENCY=NGN
```

## Important Conventions

- **API versioning**: All endpoints under `/api/v1/`
- **Timestamps**: Every model has `created_at`, `updated_at` (UTC, server-side)
- **UUIDs**: Primary keys are UUIDs, stored as strings in SQLite
- **Errors**: Return HTTPException with status codes; client catches as APIError
- **Offline**: Client caches data locally, syncs when server available

---

## WebSocket Implementation (Real-time Updates)

**Current State**: Placeholder endpoint exists at `/ws` but is not fully implemented. Follow this pattern to add real-time sync:

### Server Pattern

```python
# In server/app/main.py
from fastapi import WebSocketDisconnect
from typing import Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        """Send to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """Real-time sync for inventory, POS, etc."""
    try:
        # Verify token before accepting
        user_id = verify_token(token)
        if not user_id:
            await websocket.close(code=1008, reason="Unauthorized")
            return
        
        await manager.connect(websocket)
        
        while True:
            data = await websocket.receive_json()
            # Process subscription/unsubscription requests
            # Broadcast updates to relevant clients
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**When to use WebSocket**:
- POS sales in real-time (price updates, inventory sync)
- Inventory changes across multiple clients
- Stock alerts when items hit low threshold
- Multi-user notifications (user logged in/out)

### Client Pattern

```python
# In client/app/api/websocket_client.py
import asyncio
from websockets.client import connect

class WebSocketClient:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.websocket = None
        self.running = False
    
    async def connect(self):
        """Establish WebSocket connection."""
        try:
            self.websocket = await connect(f"{self.url}?token={self.token}")
            self.running = True
            asyncio.create_task(self._listen())
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
    
    async def _listen(self):
        """Listen for incoming messages."""
        try:
            async for message in self.websocket:
                # Parse and emit signal with data
                self.on_message(json.loads(message))
        except Exception as e:
            print(f"WebSocket error: {e}")
            self.running = False
    
    async def send(self, message: dict):
        """Send message to server."""
        if self.websocket and self.running:
            await self.websocket.send(json.dumps(message))
    
    def on_message(self, data: dict):
        """Override in subclass to handle messages."""
        pass
```

---

## Testing Conventions

### Server Tests

Tests use `pytest` with `pytest-asyncio` for async support. File structure mirrors source:

```
server/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── auth.py
│   └── models/
│       └── user.py
└── tests/
    ├── conftest.py
    ├── test_api/
    │   └── test_auth.py
    └── test_models/
        └── test_user.py
```

**Test Pattern**:

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.base import Base
from app.database import async_session_factory

@pytest.fixture
async def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        yield session
    
    await engine.dispose()

@pytest.fixture
async def client(test_db):
    """Create test client with mocked database."""
    from fastapi.testclient import TestClient
    from app.main import app
    
    # Override get_db dependency
    app.dependency_overrides[get_db] = lambda: test_db
    yield TestClient(app)
    app.dependency_overrides.clear()

# tests/test_api/test_auth.py
@pytest.mark.asyncio
async def test_login_success(client, test_db):
    """Test successful login."""
    # Create test user
    user = User(
        username="testuser",
        email="test@test.com",
        hashed_password=get_password_hash("password123"),
        first_name="Test",
        last_name="User",
        role=UserRole.CASHIER,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    
    # Test login
    response = client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123"
    })
    
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_invalid_password(client, test_db):
    """Test login with wrong password."""
    response = client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
```

**Key Testing Rules**:
- Use `@pytest.mark.asyncio` for async tests
- Always `await` database operations
- Use in-memory SQLite (`:memory:`) for speed
- Override `get_db` dependency to inject test database
- Test both happy path and error cases
- Fixtures should be async if they do I/O

### Client Tests

Client tests mock the API and focus on UI logic:

```python
# client/tests/test_login_window.py
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication

def test_login_window_shows_error_on_invalid_credentials(qtbot):
    """Test error display on login failure."""
    app = QApplication.instance() or QApplication([])
    
    window = LoginWindow()
    qtbot.addWidget(window)
    
    with patch('app.api.api_client.login') as mock_login:
        mock_login.side_effect = APIError("Invalid credentials", 401)
        
        # Simulate login attempt
        window.username_input.setText("testuser")
        window.password_input.setText("wrong")
        window.login_btn.click()
        
        # Check error message displayed
        assert window.error_label.text() == "Invalid credentials"
```

---

## Database Migrations with Alembic

### Creating a Migration

```bash
cd server

# 1. Add a new model with changes
# Edit app/models/customer.py

# 2. Generate migration (auto-detects model changes)
alembic revision --autogenerate -m "Add customer loyalty points field"

# 3. Review generated migration in alembic/versions/
# Edit if needed (remove unrelated changes)

# 4. Run migration
alembic upgrade head

# 5. Verify database
python -c "from app.database import engine; print('Success')"
```

### Migration File Pattern

```python
# alembic/versions/20250115_143022_add_loyalty_points.py
from alembic import op
import sqlalchemy as sa

revision = '143022abcd12'
down_revision = 'abc12efgh34'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add loyalty_points column to customers."""
    op.add_column('customers', sa.Column('loyalty_points', sa.Integer(), nullable=False, server_default='0'))
    op.create_index(op.f('ix_customers_loyalty_points'), 'customers', ['loyalty_points'])

def downgrade() -> None:
    """Remove loyalty_points column."""
    op.drop_index(op.f('ix_customers_loyalty_points'), table_name='customers')
    op.drop_column('customers', 'loyalty_points')
```

**Migration Rules**:
- Always write `downgrade()` to allow rollback
- Use `op.add_column()`, `op.drop_column()`, `op.rename_table()`
- For data transformations, use `op.execute(text("UPDATE ..."))`
- Test migrations on a backup database first
- Keep migrations small (one logical change per revision)

### Rolling Back

```bash
# Rollback 1 migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc12efgh34

# Show history
alembic history
```

### Common Alembic Issues

**SQLite limitations**: SQLite doesn't support all ALTER TABLE operations. Use `render_as_batch=True` in env.py:

```python
# In alembic/env.py - already configured
context.configure(
    connection=connection, 
    target_metadata=target_metadata,
    render_as_batch=True  # Enables batch operations for SQLite
)
```

---

## Deployment & Production Setup

### Docker Deployment

Uncomment and customize the `api_server` service in `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    # ... existing config

  redis:
    image: redis:7-alpine
    # ... existing config

  api_server:
    build:
      context: ./server
      dockerfile: Dockerfile
    container_name: sparkle_api
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379/0
      DEBUG: "false"
      SECRET_KEY: ${SECRET_KEY}  # Set via .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - sparkle_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:

networks:
  sparkle_network:
    driver: bridge
```

**Create `server/Dockerfile`**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations and start server
CMD ["bash", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

### Production Environment (.env.production)

```bash
# Database
USE_SQLITE=False
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=retail_erp
POSTGRES_USER=retail_admin
POSTGRES_PASSWORD=<strong-password>

# Redis
REDIS_HOST=redis
REDIS_PASSWORD=<strong-password>

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
DEBUG=False
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Logging
LOG_LEVEL=WARNING
```

**Start with Docker Compose**:

```bash
docker-compose --env-file .env.production up -d
docker-compose logs -f api_server
```

### Production Checklist

- [ ] Set `DEBUG=False` in environment
- [ ] Generate secure `SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Use PostgreSQL (not SQLite) in production
- [ ] Set strong `POSTGRES_PASSWORD` and `REDIS_PASSWORD`
- [ ] Enable CORS only for your domain(s)
- [ ] Set up log aggregation (send logs to external service)
- [ ] Configure SSL/TLS (use reverse proxy like nginx)
- [ ] Run `alembic upgrade head` before starting
- [ ] Set database connection pooling appropriately
- [ ] Monitor Redis memory and set `maxmemory-policy`

### Example Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Error Handling

### Custom Exception Hierarchy

All exceptions inherit from `AppException` in `app/core/exceptions.py`:

```python
from app.core.exceptions import (
    NotFoundException,        # 404
    BadRequestException,      # 400
    UnauthorizedException,    # 401
    ForbiddenException,       # 403
    ConflictException,        # 409
    ValidationException,      # 422
)

# Usage in endpoints
@router.get("/items/{item_id}")
async def get_item(item_id: UUID, db: DBSession):
    item = await get_item_by_id(item_id, db)
    if not item:
        raise NotFoundException(f"Item {item_id} not found")
    return item
```

### Exception Response Format

All exceptions return consistent JSON:

```json
{
    "success": false,
    "message": "Resource not found",
    "details": null
}
```

In debug mode, `details` contains stack trace. In production, it's null for security.

### Client Error Handling

```python
from app.api import APIError

try:
    result = api_client.get_items()
except APIError as e:
    if e.status_code == 401:
        # Handle token expiration - refresh or re-login
        pass
    elif e.status_code == 403:
        # Handle permission denial
        QMessageBox.warning(self, "Permission Denied", e.message)
    else:
        # Generic error
        logger.error(f"API Error: {e}")
```

---

## Initialization & Seeding

### First-Time Setup

```bash
cd server

# 1. Create database and tables
python init_dev_db.py

# 2. Seed initial admin user and location
python seed_admin.py
# Creates:
#   - Location: "Main Warehouse" (code: WH01)
#   - User: admin / admin123 (SUPER_ADMIN role)

# 3. Verify connection
alembic current  # Should show current database version

# 4. Start server
uvicorn app.main:app --reload
```

**Seed script location**: `server/seed_admin.py`

Customize for your needs (add more locations, users, categories):

```python
async def seed_data():
    async with async_session_factory() as session:
        # Create locations
        for name, code in [("Main", "WH01"), ("Branch", "WH02")]:
            location = Location(name=name, code=code, is_active=True)
            session.add(location)
        
        # Create categories, suppliers, etc.
        
        await session.commit()
```

---

## Debugging Tips

### Server Debugging

```python
# Add debug logging in endpoints
from app.config import settings

@router.get("/items")
async def get_items(db: DBSession):
    if settings.debug:
        print(f"Fetching items from database")  # Shows in console
    
    items = await get_all_items(db)
    return items

# View SQL queries (enable in config)
# Set echo=True in create_async_engine
# All generated SQL will print to console
```

### Client Debugging

```python
# Enable logging in client
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("retailpro")

# In API client methods
logger.debug(f"Making request: {method} {url}")
logger.info(f"Response: {response.status_code}")
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `sqlalchemy.exc.OperationalError: no such table` | Migration not run | `alembic upgrade head` |
| `401 Unauthorized` | Token expired or invalid | Refresh token or re-login |
| `Cannot connect to server` | Server not running or wrong URL | Check `SERVER_URL` in .env |
| `Foreign key constraint failed` | Related record missing | Ensure parent record exists before insert |
| `WebSocket connection refused` | Server not listening on /ws | Implement WebSocket endpoint |

---

## Additional Resources

- **FastAPI Docs**: Official async patterns https://fastapi.tiangolo.com/async-concurrency/
- **SQLAlchemy 2.0**: Async ORM guide https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **PySide6**: Signal/Slot threading https://doc.qt.io/qt-6/qthread.html
- **Alembic**: Migration best practices https://alembic.sqlalchemy.org/en/latest/
- **Pytest**: Async testing https://pytest-asyncio.readthedocs.io/
