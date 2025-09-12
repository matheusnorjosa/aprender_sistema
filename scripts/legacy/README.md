# 🐍 Legacy Scripts Directory

This directory contains historical Python scripts that were moved during the repository cleanup process.

## Contents

### 🔍 Analysis Scripts
- `analyze_extracted_data.py` - Analysis of extracted data from spreadsheets
- `database_analysis.py` - Database structure analysis
- `database_analysis_sqlite.py` - SQLite-specific database analysis
- `detailed_analysis.py` - Detailed system analysis
- `investigate_system.py` - System investigation utilities
- `consolidate_all_data.py` - Data consolidation scripts

### 🔐 OAuth & Authentication Scripts
- `authorize_oauth.py` - OAuth authorization utilities
- `direct_oauth.py` - Direct OAuth implementation
- `quick_oauth_test.py` - Quick OAuth testing
- `reauthorize_google_calendar.py` - Google Calendar reauthorization
- `security_test_auth.py` - Authentication security testing
- `setup_google_oauth.py` - Google OAuth setup
- `simple_oauth.py` - Simplified OAuth implementation

### 🗄️ Data Migration Scripts
- `extract_all_data.py` - Complete data extraction from spreadsheets
- `extract_controle_fixed.py` - Control data extraction (fixed version)
- `extract_controle_silent.py` - Silent control data extraction
- `check_migrated_users.py` - User migration verification

### 👥 User & Groups Scripts
- `create_groups.py` - Django groups creation
- `setup_groups_simple.py` - Simplified groups setup
- `setup_local_settings.py` - Local environment setup

### 🛠️ Utilities & Testing
- `lint.py` - Code linting utilities
- `performance_test.py` - Performance testing scripts
- `security_check.py` - Security verification
- `validate_dashboard_tests.py` - Dashboard tests validation

## Status

**Status**: Archived for reference only  
**Date Moved**: 2025-09-11  
**Reason**: Repository cleanup - Phase 4  

## Usage Guidelines

1. **Historical Reference**: These scripts contain valuable logic that may be needed for future reference
2. **Not in Active Use**: Scripts are no longer part of the active development workflow
3. **Migration Path**: Logic from these scripts has been integrated into:
   - Django management commands (`core/management/commands/`)
   - Service classes (`core/services/`)
   - Automated scripts (`scripts/`)

## Recovery

If any script logic is needed:
1. Review the original script in this directory
2. Extract the relevant logic
3. Integrate into the appropriate Django component (management command, service, etc.)
4. Follow current coding standards and testing practices

## Cleanup Schedule

These scripts can be reviewed for permanent removal after:
- 6 months of successful system operation
- Confirmation that all logic has been properly migrated
- No outstanding dependencies or references

---
*Legacy scripts archived during repository cleanup - Phase 4*  
*Date: 2025-09-11*