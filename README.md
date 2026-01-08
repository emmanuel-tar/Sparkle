# RetailPro ERP - Sparkle

> **Seamless and Operational ERP for Retail Business**

A full-featured retail ERP system with Python client-server architecture. Back office server uses FastAPI + PostgreSQL + Redis, while front office clients use PySide6 + SQLite with offline capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  BACK OFFICE SERVER                         │
│  Python + FastAPI + PostgreSQL + Redis + WebSocket         │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴─────────────────────────────────────┐
        │               LOCAL AREA NETWORK                     │
        └───────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────▼─────────────────────────────────────┐
│               FRONT OFFICE CLIENTS                   │
│  Python + PySide6 + SQLite                           │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Server Setup

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Setup server environment
cd server
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Client Setup

```bash
cd client
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run client
python main.py
```

## Project Structure

```
Sparkle/
├── server/          # Back Office Server (FastAPI)
├── client/          # Front Office Client (PySide6)
├── docker-compose.yml
└── docs/
```

## License

See [LICENSE](LICENSE) file.
