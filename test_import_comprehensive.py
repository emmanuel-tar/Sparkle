"""
Inventory Import Test Suite

Comprehensive tests for the inventory import/export functionality.
Verifies both backend API and client integration.
"""

import csv
import io
import asyncio
import httpx
from pathlib import Path
from typing import Dict, Any, List, Tuple


class ImportTestSuite:
    """Test suite for inventory import functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000/api/v1", username: str = "admin", password: str = "admin123"):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = None
        self.client = None
        self.results = []
    
    async def setup(self):
        """Initialize HTTP client and authenticate."""
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        try:
            resp = await self.client.post(
                "/auth/login",
                json={"username": self.username, "password": self.password}
            )
            if resp.status_code != 200:
                print(f"❌ Authentication failed: {resp.text}")
                return False
            self.token = resp.json()["access_token"]
            print(f"✓ Authenticated as {self.username}")
            return True
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authenticated headers."""
        return {"Authorization": f"Bearer {self.token}"}
    
    def _create_test_csv(self, name: str, content: List[List[str]], encoding: str = "utf-8") -> Tuple[Path, str]:
        """Create a test CSV file."""
        file_path = Path(f"test_{name}.csv")
        with open(file_path, "w", newline="", encoding=encoding) as f:
            writer = csv.writer(f)
            writer.writerows(content)
        return file_path, file_path.name
    
    def _log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"       {details}")
        self.results.append({"test": test_name, "passed": passed, "details": details})
    
    async def test_template_download(self):
        """Test 1: Download import template."""
        print("\n[1] Testing Template Download...")
        try:
            resp = await self.client.get("/inventory/import-template", headers=self._get_headers())
            passed = resp.status_code == 200 and b"SKU" in resp.content
            self._log_test("Download template", passed, f"Status: {resp.status_code}")
        except Exception as e:
            self._log_test("Download template", False, str(e))
    
    async def test_valid_import_utf8(self):
        """Test 2: Valid UTF-8 import with all required fields."""
        print("\n[2] Testing Valid UTF-8 Import...")
        content = [
            ["SKU", "Name", "Selling Price", "Location", "Category", "Supplier", "Stock", "Min Stock", "Cost Price", "Unit"],
            ["TEST-UTF8-001", "UTF-8 Product", "1000", "Main Store", "General", "", "100", "10", "500", "pcs"],
            ["TEST-UTF8-002", "UTF-8 Product 2", "2000", "Main Store", "General", "", "50", "5", "1000", "pcs"],
        ]
        file_path, file_name = self._create_test_csv("utf8_valid", content, "utf-8")
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "text/csv")}
                resp = await self.client.post(
                    "/inventory/import",
                    headers=self._get_headers(),
                    files=files
                )
            
            passed = resp.status_code == 200
            result = resp.json() if passed else {}
            details = f"Imported: {result.get('imported_count', 0)}, Errors: {len(result.get('errors', []))}"
            self._log_test("Valid UTF-8 import", passed, details)
        except Exception as e:
            self._log_test("Valid UTF-8 import", False, str(e))
        finally:
            file_path.unlink()
    
    async def test_valid_import_latin1(self):
        """Test 3: Valid Latin-1 import (special characters)."""
        print("\n[3] Testing Valid Latin-1 Import...")
        content = [
            ["SKU", "Name", "Selling Price", "Location"],
            ["TEST-LATIN-001", "Café Product", "1500", "Main Store"],
        ]
        file_path, file_name = self._create_test_csv("latin1_valid", content, "latin-1")
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "text/csv")}
                resp = await self.client.post(
                    "/inventory/import",
                    headers=self._get_headers(),
                    files=files
                )
            
            passed = resp.status_code == 200
            result = resp.json() if passed else {}
            details = f"Encoding: {result.get('encoding_used')}, Items: {result.get('total_processed', 0)}"
            self._log_test("Valid Latin-1 import", passed, details)
        except Exception as e:
            self._log_test("Valid Latin-1 import", False, str(e))
        finally:
            file_path.unlink()
    
    async def test_missing_required_fields(self):
        """Test 4: Import with missing required fields."""
        print("\n[4] Testing Missing Required Fields...")
        content = [
            ["SKU", "Name", "Location"],  # Missing Selling Price
            ["TEST-MISS-001", "Missing Price", "Main Store"],
        ]
        file_path, file_name = self._create_test_csv("missing_fields", content)
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "text/csv")}
                resp = await self.client.post(
                    "/inventory/import",
                    headers=self._get_headers(),
                    files=files
                )
            
            # Should fail because Selling Price is missing
            passed = resp.status_code == 400
            details = f"Status: {resp.status_code}, Expected: 400"
            self._log_test("Missing required fields detection", passed, details)
        except Exception as e:
            self._log_test("Missing required fields detection", False, str(e))
        finally:
            file_path.unlink()
    
    async def test_invalid_selling_price(self):
        """Test 5: Import with invalid selling price."""
        print("\n[5] Testing Invalid Selling Price...")
        content = [
            ["SKU", "Name", "Selling Price", "Location"],
            ["TEST-PRICE-001", "Invalid Price", "invalid", "Main Store"],
            ["TEST-PRICE-002", "Negative Price", "-100", "Main Store"],
        ]
        file_path, file_name = self._create_test_csv("invalid_price", content)
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "text/csv")}
                resp = await self.client.post(
                    "/inventory/import",
                    headers=self._get_headers(),
                    files=files
                )
            
            passed = resp.status_code == 200
            result = resp.json() if passed else {}
            has_errors = len(result.get("errors", [])) >= 2
            details = f"Errors: {len(result.get('errors', []))}, Expected: >= 2"
            self._log_test("Invalid price detection", passed and has_errors, details)
        except Exception as e:
            self._log_test("Invalid price detection", False, str(e))
        finally:
            file_path.unlink()
    
    async def test_numeric_parsing(self):
        """Test 6: Numeric parsing with various formats."""
        print("\n[6] Testing Numeric Parsing...")
        content = [
            ["SKU", "Name", "Selling Price", "Stock", "Cost Price", "Location"],
            ["TEST-NUM-001", "Comma Format", "1,500.50", "100,50", "500,25", "Main Store"],
            ["TEST-NUM-002", "Dot Format", "2000.75", "75.5", "1000.25", "Main Store"],
        ]
        file_path, file_name = self._create_test_csv("numeric_parse", content)
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "text/csv")}
                resp = await self.client.post(
                    "/inventory/import",
                    headers=self._get_headers(),
                    files=files
                )
            
            passed = resp.status_code == 200
            result = resp.json() if passed else {}
            details = f"Imported: {result.get('imported_count', 0)}, Errors: {len(result.get('errors', []))}"
            self._log_test("Numeric parsing", passed and result.get('imported_count', 0) == 2, details)
        except Exception as e:
            self._log_test("Numeric parsing", False, str(e))
        finally:
            file_path.unlink()
    
    async def test_duplicate_sku_update(self):
        """Test 7: Duplicate SKU updates existing item."""
        print("\n[7] Testing Duplicate SKU Update...")
        content = [
            ["SKU", "Name", "Selling Price", "Stock", "Location"],
            ["TEST-DUP-001", "Original Item", "1000", "100", "Main Store"],
        ]
        file_path, file_name = self._create_test_csv("dup_sku", content)
        
        try:
            # First import
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "text/csv")}
                resp1 = await self.client.post(
                    "/inventory/import",
                    headers=self._get_headers(),
                    files=files
                )
            
            # Second import with same SKU but different data
            content[1] = ["TEST-DUP-001", "Updated Item", "2000", "200", "Main Store"]
            file_path.unlink()
            file_path, file_name = self._create_test_csv("dup_sku", content)
            
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "text/csv")}
                resp2 = await self.client.post(
                    "/inventory/import",
                    headers=self._get_headers(),
                    files=files
                )
            
            passed = resp1.status_code == 200 and resp2.status_code == 200
            result2 = resp2.json() if passed else {}
            details = f"First import: imported {resp1.json().get('imported_count')}, Second: updated {result2.get('updated_count', 0)}"
            self._log_test("Duplicate SKU update", passed and result2.get('updated_count', 0) == 1, details)
        except Exception as e:
            self._log_test("Duplicate SKU update", False, str(e))
        finally:
            file_path.unlink()
    
    async def test_empty_rows_skip(self):
        """Test 8: Empty rows are skipped."""
        print("\n[8] Testing Empty Row Skipping...")
        content = [
            ["SKU", "Name", "Selling Price", "Location"],
            ["TEST-EMPTY-001", "Product 1", "1000", "Main Store"],
            ["", "", "", ""],  # Empty row
            ["TEST-EMPTY-002", "Product 2", "2000", "Main Store"],
        ]
        file_path, file_name = self._create_test_csv("empty_rows", content)
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "text/csv")}
                resp = await self.client.post(
                    "/inventory/import",
                    headers=self._get_headers(),
                    files=files
                )
            
            passed = resp.status_code == 200
            result = resp.json() if passed else {}
            details = f"Imported: {result.get('imported_count', 0)}, Expected: 2"
            self._log_test("Empty row skipping", passed and result.get('imported_count', 0) == 2, details)
        except Exception as e:
            self._log_test("Empty row skipping", False, str(e))
        finally:
            file_path.unlink()
    
    async def test_export_inventory(self):
        """Test 9: Export inventory to CSV."""
        print("\n[9] Testing Inventory Export...")
        try:
            resp = await self.client.get("/inventory/export", headers=self._get_headers())
            passed = resp.status_code == 200 and b"SKU" in resp.content
            details = f"Status: {resp.status_code}, Size: {len(resp.content)} bytes"
            self._log_test("Export inventory", passed, details)
        except Exception as e:
            self._log_test("Export inventory", False, str(e))
    
    async def test_import_export_roundtrip(self):
        """Test 10: Export and re-import data."""
        print("\n[10] Testing Import/Export Roundtrip...")
        try:
            # Export
            resp_export = await self.client.get("/inventory/export", headers=self._get_headers())
            if resp_export.status_code != 200:
                self._log_test("Import/export roundtrip", False, "Export failed")
                return
            
            # Import the exported file
            export_data = resp_export.content
            files = {"file": ("roundtrip.csv", io.BytesIO(export_data), "text/csv")}
            resp_import = await self.client.post(
                "/inventory/import",
                headers=self._get_headers(),
                files=files
            )
            
            passed = resp_import.status_code == 200
            result = resp_import.json() if passed else {}
            details = f"Exported items re-imported: {result.get('total_processed', 0)}"
            self._log_test("Import/export roundtrip", passed, details)
        except Exception as e:
            self._log_test("Import/export roundtrip", False, str(e))
    
    async def run_all_tests(self):
        """Run all tests."""
        if not await self.setup():
            return
        
        print("\n" + "="*60)
        print("INVENTORY IMPORT/EXPORT TEST SUITE")
        print("="*60)
        
        await self.test_template_download()
        await self.test_valid_import_utf8()
        await self.test_valid_import_latin1()
        await self.test_missing_required_fields()
        await self.test_invalid_selling_price()
        await self.test_numeric_parsing()
        await self.test_duplicate_sku_update()
        await self.test_empty_rows_skip()
        await self.test_export_inventory()
        await self.test_import_export_roundtrip()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        print(f"Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed < total:
            print("\nFailed Tests:")
            for r in self.results:
                if not r["passed"]:
                    print(f"  ❌ {r['test']}: {r['details']}")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.aclose()


async def main():
    """Run the test suite."""
    suite = ImportTestSuite()
    try:
        await suite.run_all_tests()
    finally:
        await suite.cleanup()


if __name__ == "__main__":
    print("Starting Inventory Import/Export Test Suite...")
    print("Make sure the server is running on http://localhost:8000\n")
    asyncio.run(main())
