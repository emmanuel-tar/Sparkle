# Inventory Import/Export - Quick Reference

## ⚡ Quick Start

### Import Inventory
1. **Inventory Management** → **⚙️ Tools** → **📥 Import Inventory**
2. Select CSV file or **📝 Download Template**
3. Click **⬆️ Import**
4. Check **Summary** tab for results
5. Check **Errors** tab if there are issues

### Export Inventory
1. **Inventory Management** → **⚙️ Tools** → **📤 Export Inventory**
2. Choose save location
3. Done! CSV file with current date in filename

### Download Template
1. **Inventory Management** → **⚙️ Tools** → **📝 Download Template**
2. Use as reference for your CSV format

---

## 📋 CSV Requirements

### Minimum Columns (Required)
```
SKU,Name,Selling Price
```

### Full Format (Recommended)
```
SKU,Barcode,Name,Description,Category,Location,Supplier,Stock,Min Stock,Cost Price,Selling Price,Unit
```

### Example Row
```
PROD-001,123456789,Widget A,Premium widget,Electronics,Main Store,Supplier A,100,10,500,1000,pcs
```

---

## ✅ Validation Checklist

- [ ] SKU is unique and not blank
- [ ] Name is not blank
- [ ] Selling Price is > 0 (numeric)
- [ ] Location exists (or use default)
- [ ] Category matches existing categories (if provided)
- [ ] Supplier matches existing suppliers (if provided)
- [ ] Stock/Min Stock are valid numbers
- [ ] Cost Price is valid number (if provided)
- [ ] CSV encoding is UTF-8, Latin-1, or CP1252

---

## 🔢 Number Format Examples

| Format | Accepted? | Note |
|--------|-----------|------|
| `1000` | ✓ | Basic integer |
| `1000.50` | ✓ | With decimals |
| `1,000` | ✓ | With comma separator |
| `1,000.50` | ✓ | Comma + decimal |
| `-500` | ✓ | Negative allowed |
| `abc` | ✗ | Letters not allowed |
| `$1000` | ✗ | Currency symbol not allowed |

---

## 🔧 API Endpoints

### Import
```
POST /api/v1/inventory/import
Header: Authorization: Bearer <token>
Body: multipart/form-data {file: <csv>}

Response: {
  "success": true,
  "imported_count": 10,
  "updated_count": 5,
  "total_processed": 15,
  "errors": [],
  "encoding_used": "utf-8",
  "message": "..."
}
```

### Export
```
GET /api/v1/inventory/export
Header: Authorization: Bearer <token>

Response: CSV binary data
```

### Template
```
GET /api/v1/inventory/import-template

Response: CSV template file
```

---

## 🚨 Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Missing or empty SKU` | Provide unique SKU for each product |
| `Missing or empty Selling Price` | Add price > 0 for each item |
| `Invalid Selling Price 'value'` | Use valid number (no letters/symbols) |
| `Location not found` | Check location name matches exactly |
| `Unable to decode file` | Save CSV as UTF-8 encoding |
| `Missing required columns` | Ensure SKU, Name, Selling Price columns exist |

---

## 📊 Import Response Meanings

| Field | Meaning |
|-------|---------|
| `success` | All rows processed (may have errors) |
| `imported_count` | New items created |
| `updated_count` | Existing items updated |
| `total_processed` | imported_count + updated_count |
| `errors` | List of rows with problems |
| `encoding_used` | Detected file encoding |

---

## 🔐 Permissions Required

- **Import**: `manage_inventory` permission
- **Export**: `view_reports` permission
- **Movements**: `view_reports` permission

---

## 🎯 Tips & Best Practices

1. **Always backup** before large imports
2. **Download template first** to see exact format
3. **Test small** - import 5 items first
4. **Review errors** - always check error tab
5. **Verify stock** after import to ensure accuracy
6. **Use unique SKUs** - duplicates update existing items
7. **Be consistent** with location/category/supplier names
8. **Document changes** - note what was imported and when

---

## 📈 Performance Guide

| File Size | Time | Notes |
|-----------|------|-------|
| < 100 items | < 2s | Quick |
| 100-1000 items | 5-10s | Normal |
| 1000+ items | 30-60s | May take longer |

For very large imports, split into multiple files.

---

## 🧪 Testing

Run comprehensive tests:
```bash
python test_import_comprehensive.py
```

Tests:
- Template download
- UTF-8 import
- Latin-1 import
- Required field validation
- Price validation
- Numeric parsing
- Duplicate updates
- Empty row handling
- Export functionality
- Roundtrip (export + import)

---

## 📚 Full Documentation

See `INVENTORY_IMPORT_GUIDE.md` for:
- Detailed feature descriptions
- Complete API documentation
- Troubleshooting guide
- Examples and use cases
- Data integrity information

---

## 💬 Support

1. Check this quick reference
2. Review error messages
3. Consult INVENTORY_IMPORT_GUIDE.md
4. Run test suite for validation
5. Check server logs
6. Contact administrator
