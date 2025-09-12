# 📁 Archive Directory

This directory contains historical files that were moved during the repository cleanup process.

## Contents

### 📊 Spreadsheets (`spreadsheets/`)
Contains the original Excel files that were used before the digital system:
- `superintendencia.xlsx` - Historical superintendent data
- `produtos.xlsx` - Product/program information
- Various program-specific spreadsheets (ACerta, Vidas, IDEB10, etc.)

**Status**: Archived for reference only. Data has been migrated to the Django database.

### 📄 Temporary Data (`temp_data/`)
Contains extracted JSON files that were generated during data migration:
- `extracted_*.json` - Various data extractions from original spreadsheets
- Large files used for one-time data import

**Status**: Can be safely deleted after confirming successful data migration.

## Cleanup Guidelines

1. **Spreadsheets**: Keep as historical reference until system is fully stable
2. **Temp Data**: Can be deleted after 3 months of successful operation
3. **Review**: Check this archive quarterly for files that can be permanently removed

## Recovery

If any historical data is needed:
1. Check the original spreadsheets in the `spreadsheets/` directory
2. Use the Django admin interface to verify if data was properly migrated
3. Contact the system administrator if data recovery is needed

---
*Archive created during repository cleanup - Phase 4*
*Date: 2025-09-11*