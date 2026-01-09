# Inventory Import/Export Guide

## Overview

The inventory import/export feature allows you to bulk import products into your system and export your current inventory as CSV files. This is useful for:

- Initial system setup with bulk product data
- Regular inventory sync from suppliers
- Backup and migration between systems
- Data analysis and reporting

## Supported Encodings

The import system automatically detects and handles:
- **UTF-8** (with and without BOM)
- **Latin-1** (ISO-8859-1)
- **CP1252** (Windows Western)

## CSV Format

### Required Columns
- **SKU** - Stock Keeping Unit (must be unique)
- **Name** - Product name
- **Selling Price** - Sale price (must be > 0)

### Optional Columns
- **Location** - Physical location (defaults to user's location)
- **Barcode** - Barcode number
- **Description** - Product description
- **Category** - Product category name
- **Supplier** - Supplier name
- **Stock** - Current stock quantity
- **Min Stock** - Minimum stock level
- **Cost Price** - Cost/purchase price
- **Unit** - Unit of measurement (default: "pcs")

### Example CSV

```csv
SKU,Name,Selling Price,Location,Category,Stock,Cost Price
PROD-001,Widget A,1500,Main Store,Electronics,100,750
PROD-002,Widget B,2000,Main Store,Electronics,50,1000
PROD-003,Gadget X,3500,Branch 1,Gadgets,200,1750
```

## Using the Import Feature

### From Client UI

1. Open the **Inventory Management** view
2. Click **⚙️ Tools** menu
3. Select **📥 Import Inventory**
4. A dialog will open with options to:
   - Browse and select a CSV file
   - Download a template for reference
   - Monitor import progress
   - View detailed error reports

### Steps

1. **Select File**: Click "📁 Browse..." to select your CSV file
2. **Download Template** (Optional): Click "📝 Download Template" to see the expected format
3. **Import**: Click "⬆️ Import" to start the import process
4. **Review Results**: 
   - Summary tab shows overall statistics
   - Errors tab lists any rows that failed with reasons

### API Endpoint

```
POST /api/v1/inventory/import
```

**Headers:**
```
Authorization: Bearer <token>
```

**Body:** (multipart/form-data)
```
file: <CSV file>
```

**Response:**
```json
{
  "success": true,
  "imported_count": 10,
  "updated_count": 5,
  "total_processed": 15,
  "errors": [],
  "encoding_used": "utf-8",
  "message": "Imported 10 new items, updated 5 existing items"
}
```

## Error Handling

The system provides detailed error messages for each problematic row:

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Missing or empty SKU` | SKU column is blank | Provide a unique SKU for each product |
| `Missing or empty Name` | Name column is blank | Add a product name |
| `Missing or empty Selling Price` | Price column is blank | Add a selling price > 0 |
| `Invalid Selling Price 'value'` | Price is not a valid number or <= 0 | Use valid positive numbers |
| `Location 'name' not found` | Location doesn't exist | Check location name or use user's default |
| `Unexpected error: ...` | Database or system error | Check CSV format or contact admin |

## Validation Rules

### Price Validation
- Selling Price must be present and > 0
- Cost Price is optional, if provided must be numeric
- Supports formats: `1000`, `1,000`, `1000.50`, `1,000.50`

### Stock Levels
- Stock, Min Stock values are numeric and optional
- Negative values are allowed (with configuration)

### Location & Category
- Location must exist or user must have a default location
- Category is optional; if provided, must match existing category
- Supplier is optional; if provided, must match existing supplier

### Duplicate Handling
- **New SKU**: Creates new product
- **Existing SKU**: Updates the existing product with new data
- **Barcode duplicates**: Not prevented (can occur during updates)

## Export Feature

### Using Export

1. Click **⚙️ Tools** menu
2. Select **📤 Export Inventory**
3. Choose save location
4. CSV file will be saved with current date in filename

### Export Includes

All active inventory items with:
- SKU, Barcode, Name, Description
- Category, Location, Supplier
- Current Stock, Min Stock Level
- Cost Price, Selling Price, Unit

## Download Template

1. Click **⚙️ Tools** menu
2. Select **📝 Download Template**
3. Save the template CSV file
4. Fill in your product data using the template structure

## Testing

### Run Comprehensive Tests

```bash
python test_import_comprehensive.py
```

This will test:
- Template download
- UTF-8 import
- Latin-1 import
- Missing required fields
- Invalid prices
- Numeric parsing
- Duplicate SKU updates
- Empty row skipping
- Export functionality
- Import/export roundtrip

### Test Results

The test suite provides:
- Pass/fail status for each test
- Detailed error messages
- Performance metrics
- Success rate summary

## Troubleshooting

### "Unable to decode file" Error
- Ensure CSV is saved with a supported encoding (UTF-8, Latin-1, or CP1252)
- Try re-saving with UTF-8 encoding

### "Location not found" Error
- Check that location names match exactly (case-insensitive)
- Ensure location exists in the system

### "Selling Price" Validation Fails
- Verify price is a positive number
- Check for accidental letters or symbols
- Use formats: `1000` or `1000.50` (not `$1,000`)

### Import Hangs or Times Out
- Check CSV file size (very large files may take longer)
- Break into smaller files if needed
- Check server logs for database issues

## Permissions

To use import/export features, user must have:
- **manage_inventory** permission for import
- **view_reports** permission for export
- **view_reports** permission for movement audit log

## Performance

Import performance depends on:
- CSV file size
- Number of locations, categories, suppliers
- Database load
- System resources

### Typical Performance
- 100 items: < 2 seconds
- 1,000 items: 5-10 seconds
- 10,000 items: 30-60 seconds

## Data Integrity

### Rollback on Error
If a database error occurs during import:
- No items are committed
- CSV import is rolled back
- User receives error message

### Validation Occurs
- Before database operations
- All rows are validated
- Errors are collected and reported

## Best Practices

1. **Download Template First**: Use the template to ensure correct format
2. **Validate Data**: Check CSV for required fields and valid values
3. **Backup**: Export inventory before major imports
4. **Test Small**: Import small sample first before bulk import
5. **Review Errors**: Always check error tab for any issues
6. **Monitor Stock**: Verify imported stock levels after import
7. **Document Changes**: Note what was imported and when

## Examples

### Basic Import
```csv
SKU,Name,Selling Price
PROD-001,Product A,1000
PROD-002,Product B,2000
```

### Complete Import
```csv
SKU,Barcode,Name,Description,Category,Location,Supplier,Stock,Min Stock,Cost Price,Selling Price,Unit
PROD-001,123456,Widget,High-quality widget,Electronics,Main Store,Supplier A,100,10,500,1000,pcs
PROD-002,123457,Gadget,Best gadget,Gadgets,Branch 1,Supplier B,50,5,1500,3000,pcs
```

## Support

For issues or questions:
1. Check the error messages and this guide
2. Review test output from `test_import_comprehensive.py`
3. Check server logs for detailed error information
4. Contact system administrator
