# Project Change Log - RetailPro ERP

## [2026-01-09] - Inventory Import/Export Complete Implementation

### Added

- **Comprehensive Inventory Import/Export System**:
  - Enhanced backend API with robust validation and error handling
  - Multi-encoding support (UTF-8, Latin-1, CP1252)
  - Duplicate detection (updates existing items by SKU)
  - Atomic transactions with rollback on errors
  - Professional client-side UI with progress tracking and error reporting
  - 10-test comprehensive test suite for validation
  - Complete user documentation and quick reference guides

- **Backend API Improvements** (`server/app/api/v1/inventory.py`):
  - Field validation for required columns (SKU, Name, Selling Price)
  - Advanced numeric parsing (supports: `1000`, `1000.50`, `1,000`, `1,000.50`)
  - Detailed error messages with row numbers and field details
  - Database rollback on errors to ensure data integrity
  - Enhanced import response with metadata (imported_count, updated_count, encoding_used)
  - Empty row automatic skipping

- **Client Import Dialog** (`client/app/ui/dialogs/import_dialog.py`):
  - File browser for CSV selection
  - Template download button
  - Progress bar with visual feedback
  - Multi-threaded import worker (no UI freezing)
  - Summary tab with overall statistics
  - Errors tab with detailed error table and row numbers
  - Color-coded error display for clarity

- **Test Suite** (`test_import_comprehensive.py`):
  - 10 comprehensive test scenarios
  - Async test operations for efficiency
  - Tests for all encoding types and edge cases
  - Pass/fail reporting with detailed messages
  - Success rate summary

- **Documentation**:
  - `INVENTORY_IMPORT_GUIDE.md` - Complete feature guide with examples
  - `INVENTORY_IMPORT_QUICK_REFERENCE.md` - Quick lookup reference
  - `IMPLEMENTATION_SUMMARY.md` - Technical implementation summary

### Fixed

- ✅ Missing `datetime` import in inventory API
- ✅ Duplicate `StockAdjustment` import statement
- ✅ Orphaned code block in stock movement endpoint
- ✅ Selling price validation in import (now required)
- ✅ Numeric parsing edge cases (comma separators, etc.)
- ✅ Error handling for invalid data types

### Changed

- Updated `client/app/ui/views/inventory_view.py` to use new professional import dialog
- Enhanced import endpoint response format with additional metadata
- Improved location fallback logic (defaults to user's location if not found)

### Technical Details

- **Backend**: FastAPI async operations, SQLAlchemy ORM, transaction rollback
- **Frontend**: PySide6, QThread for background operations, custom error table
- **Testing**: Async HTTP client, CSV generation, comprehensive assertions
- **Documentation**: Markdown with examples, troubleshooting, API details

### Performance

- Small imports (< 100 items): < 2 seconds
- Medium imports (100-1000 items): 5-10 seconds
- Large imports (1000+ items): 30-60 seconds
- Supports multi-location and category lookups efficiently

### Permissions

- Import: `manage_inventory` required
- Export: `view_reports` required
- View Movements: `view_reports` required

## [2026-01-08-B] - Security & Inventory Enhancements

### Added

- **RBAC Security**: Full Role-Based Access Control implemented across backend and frontend.
  - Secured 15+ API endpoints with `require_permission` and `require_role`.
  - Dynamic UI adaptation: Sidebar and action buttons (Edit, Delete, Void) automatically hide/disable based on authorized permissions.
  - Role-specific dashboard visibility (e.g., Cashiers only see POS/Sales).
- **Inventory Import/Export (In Progress)**:
  - Backend endpoints for bulk inventory CSV export and import.
  - Standardized CSV template for data consistency.
- **Enhanced Stock Movement**: Added detailed audit trails for every inventory adjustment.

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

### Fixed

- Fixed SQLite engine configuration issue in `database.py` that prevented server startup when pooling arguments were passed to SQLite.
- Fixed `MainWindow` initialization order to ensure correct default view selection based on user permissions.
