# Test Files Directory

Place test documents in this directory for integration testing.

## Recommended Test Files

Create the following test files for comprehensive testing:

| File Name | Description | Expected Result |
|-----------|-------------|-----------------|
| `test_invoice.pdf` | Standard invoice with clear text | Should extract all fields |
| `test_receipt.png` | Image of a receipt | Should OCR and extract data |
| `test_scanned.pdf` | Scanned document (image-based PDF) | May have limited extraction |
| `test_empty.pdf` | Empty or blank PDF | Should return appropriate error |
| `test_large.pdf` | Large document (>5MB) | Should handle or reject gracefully |
| `test_multipage.pdf` | Multi-page invoice | Should merge all pages |

## How to Create Test Files

1. **test_invoice.pdf**: Use any standard invoice with:
   - Vendor name
   - Date
   - Line items with prices
   - Total amount

2. **test_receipt.png**: Take a photo or screenshot of a receipt

3. **test_scanned.pdf**: Scan a physical document to PDF

4. **test_empty.pdf**: Create a blank PDF using any PDF tool

## Running Tests with Test Files

```bash
cd backend
pytest tests/ -v
```

## Note

Test files are not committed to git (added to .gitignore) to keep the repository size small.
Create your own test files locally for testing.
