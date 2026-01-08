# Project Change Log - RetailPro ERP

## [2026-01-08] - Foundation & Development Environment

### Added

- Created foundational project structure for both server (FastAPI) and client (PySide6).
- Implemented core database models for Locations, Users, Inventory, Sales, and Customers.
- Established JWT-based authentication system with role-based access control.
- Created `init_dev_db.py` for easy SQLite database initialization during development.
- Created `seed_admin.py` to bootstrap the system with an initial super_admin user.
- Implemented `change.md` for project history tracking.

### Changed

- Refactored server models to support SQLite for development (switching from PostgreSQL-specific `UUID` and `JSONB` to generic `GUIDType` and `JSON`).
- Updated `config.py` with automatic SQLite fallback when PostgreSQL/Docker is not available.
- Modified `Sale` model to use `extra_metadata` instead of reserved `metadata` attribute.

### Fixed

- Resolved SQLAlchemy mapper initialization error caused by reserved attribute name 'metadata'.
- Fixed PySide6 client dependency issues by ensuring all required packages (`httpx`, `python-dotenv`, etc.) are installed in the same environment.
- Fixed `bcrypt` compatibility issues in the server.

### Client Progress

- Functional Login Window with server connection settings.
- **Financial Intelligence**: Real-time Margin and Markup calculations in both Product Dialog and Inventory List.
- **Location Management**: Full CRUD for physical stores and warehouses via the new Locations view.
- **Advanced Inventory Dashboard**: New columns for Location tracking and Profitability metrics (Margin %).
- **Enhanced Categorization**: Categories now show real-time product counts, supported by optimized server-side queries.
- **Dynamic Filtering**: Integrated backend-driven filtering for Locations, Categories, and Stock Status.
- **API Optimization**: Server-side joins for location and category data in inventory response.
- Basic functional POS View with cart management and customer lookup.
- Fixed navigation mapping to correctly switch between all dashboard views.
