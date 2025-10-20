#!/bin/bash
# ======================================
# 🔍 LINT SCRIPT - SISTEMA APRENDER
# Comprehensive Code Quality Checks
# ======================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Variables
FIX_MODE="${1:-check}"
REPORT_DIR="lint_reports"
EXIT_CODE=0

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "🔍 Sistema Aprender - Code Quality"
    echo "========================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[LINT]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_fix() {
    echo -e "${PURPLE}[FIX]${NC} $1"
}

# Setup reports directory
setup_reports() {
    mkdir -p $REPORT_DIR
    echo "Reports will be saved to: $REPORT_DIR"
}

# Black formatting
check_black() {
    print_step "Checking code formatting with Black..."
    
    if [ "$FIX_MODE" = "fix" ]; then
        print_fix "Auto-formatting code with Black..."
        black . --config pyproject.toml
        print_success "Code formatting applied"
    else
        if black . --check --diff --config pyproject.toml > $REPORT_DIR/black_report.txt 2>&1; then
            print_success "Black formatting check passed"
        else
            print_error "Black formatting issues found"
            echo "Run: ./scripts/lint.sh fix  or  make format"
            EXIT_CODE=1
        fi
    fi
}

# Import sorting with isort
check_isort() {
    print_step "Checking import sorting with isort..."
    
    if [ "$FIX_MODE" = "fix" ]; then
        print_fix "Auto-sorting imports with isort..."
        isort . --settings-path=pyproject.toml
        print_success "Import sorting applied"
    else
        if isort . --check-only --diff --settings-path=pyproject.toml > $REPORT_DIR/isort_report.txt 2>&1; then
            print_success "isort check passed"
        else
            print_error "Import sorting issues found"
            echo "Run: ./scripts/lint.sh fix  or  make format"
            EXIT_CODE=1
        fi
    fi
}

# Flake8 linting
check_flake8() {
    print_step "Running flake8 linting..."
    
    if flake8 . --config=setup.cfg --output-file=$REPORT_DIR/flake8_report.txt; then
        print_success "Flake8 linting passed"
    else
        print_error "Flake8 linting issues found"
        echo "Check report: $REPORT_DIR/flake8_report.txt"
        EXIT_CODE=1
    fi
}

# MyPy type checking
check_mypy() {
    print_step "Running MyPy type checking..."
    
    if command -v mypy >/dev/null 2>&1; then
        if mypy . --config-file=pyproject.toml --output=$REPORT_DIR/mypy_report.txt; then
            print_success "MyPy type checking passed"
        else
            print_warning "MyPy type checking issues found (non-critical)"
            echo "Check report: $REPORT_DIR/mypy_report.txt"
        fi
    else
        print_warning "MyPy not installed - skipping type checking"
    fi
}

# Bandit security scanning
check_bandit() {
    print_step "Running Bandit security scan..."
    
    if bandit -r . -x "/venv/,/tests/,/migrations/" -f json -o $REPORT_DIR/bandit_report.json -ll; then
        print_success "Bandit security scan passed"
    else
        print_warning "Bandit found potential security issues"
        echo "Check report: $REPORT_DIR/bandit_report.json"
    fi
    
    # Also generate text report for easy reading
    bandit -r . -x "/venv/,/tests/,/migrations/" -f txt -o $REPORT_DIR/bandit_report.txt -ll 2>/dev/null || true
}

# Safety dependency checking
check_safety() {
    print_step "Checking dependencies with Safety..."
    
    if safety check --json --output $REPORT_DIR/safety_report.json; then
        print_success "Dependency safety check passed"
    else
        print_warning "Vulnerable dependencies found"
        echo "Check report: $REPORT_DIR/safety_report.json"
    fi
    
    # Also generate text report
    safety check --output text --output $REPORT_DIR/safety_report.txt 2>/dev/null || true
}

# Django specific checks
check_django() {
    print_step "Running Django system checks..."
    
    # Basic system check
    if python manage.py check > $REPORT_DIR/django_check.txt 2>&1; then
        print_success "Django system check passed"
    else
        print_error "Django system check failed"
        echo "Check report: $REPORT_DIR/django_check.txt"
        EXIT_CODE=1
    fi
    
    # Deploy-specific checks
    print_step "Running Django deployment checks..."
    if python manage.py check --deploy > $REPORT_DIR/django_deploy_check.txt 2>&1; then
        print_success "Django deployment check passed"
    else
        print_warning "Django deployment issues found"
        echo "Check report: $REPORT_DIR/django_deploy_check.txt"
    fi
}

# Complexity checking with radon
check_complexity() {
    if command -v radon >/dev/null 2>&1; then
        print_step "Checking code complexity with Radon..."
        
        # Cyclomatic complexity
        radon cc . --json > $REPORT_DIR/complexity_cc.json
        radon cc . --min C > $REPORT_DIR/complexity_cc.txt
        
        # Maintainability index
        radon mi . --json > $REPORT_DIR/complexity_mi.json
        radon mi . --min B > $REPORT_DIR/complexity_mi.txt
        
        print_success "Complexity analysis completed"
    else
        print_warning "Radon not installed - skipping complexity checks"
    fi
}

# Documentation checking
check_docs() {
    print_step "Checking documentation..."
    
    # Check for missing docstrings
    if command -v interrogate >/dev/null 2>&1; then
        interrogate . --output $REPORT_DIR/docstring_report.txt -v
        print_success "Documentation check completed"
    else
        print_warning "Interrogate not installed - skipping docstring checks"
    fi
    
    # Check for TODO/FIXME/HACK comments
    print_step "Scanning for TODO/FIXME/HACK comments..."
    {
        echo "=== TODO Comments ==="
        grep -rn "TODO" --include="*.py" . || echo "No TODO comments found"
        echo ""
        echo "=== FIXME Comments ==="
        grep -rn "FIXME" --include="*.py" . || echo "No FIXME comments found"
        echo ""
        echo "=== HACK Comments ==="
        grep -rn "HACK" --include="*.py" . || echo "No HACK comments found"
    } > $REPORT_DIR/comments_report.txt
    
    print_success "Comment scanning completed"
}

# Pre-commit validation
check_precommit() {
    if command -v pre-commit >/dev/null 2>&1; then
        print_step "Running pre-commit hooks..."
        
        if pre-commit run --all-files > $REPORT_DIR/precommit_report.txt 2>&1; then
            print_success "Pre-commit hooks passed"
        else
            print_warning "Pre-commit hooks found issues"
            echo "Check report: $REPORT_DIR/precommit_report.txt"
        fi
    else
        print_warning "Pre-commit not installed - skipping hook validation"
    fi
}

# Generate comprehensive report
generate_report() {
    print_step "Generating comprehensive report..."
    
    SUMMARY_FILE="$REPORT_DIR/lint_summary.html"
    
    cat > $SUMMARY_FILE << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Sistema Aprender - Code Quality Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #007cba; }
        .pass { border-left-color: #28a745; }
        .warn { border-left-color: #ffc107; }
        .fail { border-left-color: #dc3545; }
        .file-list { background: #f8f9fa; padding: 10px; border-radius: 3px; }
        pre { background: #f8f9fa; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Sistema Aprender - Code Quality Report</h1>
        <p>Generated: $(date)</p>
        <p>Mode: $FIX_MODE</p>
    </div>
    
    <div class="section">
        <h2>📊 Summary</h2>
        <p>This report contains the results of comprehensive code quality checks.</p>
    </div>
    
    <div class="section">
        <h2>📁 Reports Generated</h2>
        <div class="file-list">
EOF
    
    # List all report files
    for report in $REPORT_DIR/*.txt $REPORT_DIR/*.json; do
        if [ -f "$report" ]; then
            basename "$report" >> $SUMMARY_FILE
        fi
    done
    
    cat >> $SUMMARY_FILE << 'EOF'
        </div>
    </div>
    
    <div class="section">
        <h2>🚀 Next Steps</h2>
        <ul>
            <li>Review individual report files for detailed findings</li>
            <li>Fix any critical issues (marked as FAIL)</li>
            <li>Consider addressing warnings for better code quality</li>
            <li>Run with --fix flag to auto-correct formatting issues</li>
        </ul>
    </div>
</body>
</html>
EOF
    
    print_success "Comprehensive report generated: $SUMMARY_FILE"
}

# Show help
show_help() {
    echo "Usage: ./scripts/lint.sh [MODE]"
    echo ""
    echo "Modes:"
    echo "  check  - Check code quality (default)"
    echo "  fix    - Auto-fix formatting issues"
    echo ""
    echo "Tools used:"
    echo "  - Black: Code formatting"
    echo "  - isort: Import sorting"  
    echo "  - flake8: Linting"
    echo "  - MyPy: Type checking (optional)"
    echo "  - Bandit: Security scanning"
    echo "  - Safety: Dependency vulnerabilities"
    echo "  - Django: System checks"
    echo ""
    echo "Examples:"
    echo "  ./scripts/lint.sh"
    echo "  ./scripts/lint.sh check"
    echo "  ./scripts/lint.sh fix"
}

# Main function
main() {
    case "$FIX_MODE" in
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
        "check"|"fix"|*)
            print_header
            setup_reports
            
            # Core formatting and linting
            check_black
            check_isort
            check_flake8
            
            # Advanced checks (only in check mode)
            if [ "$FIX_MODE" = "check" ]; then
                check_mypy
                check_bandit
                check_safety
                check_django
                check_complexity
                check_docs
                check_precommit
                generate_report
            fi
            ;;
    esac
    
    # Final status
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}"
        echo "========================================"
        echo "🎉 Code quality checks completed!"
        echo "========================================"
        echo -e "${NC}"
        if [ "$FIX_MODE" = "check" ]; then
            echo "Reports available in: $REPORT_DIR"
        fi
    else
        echo -e "${RED}"
        echo "========================================"
        echo "❌ Code quality issues found!"
        echo "========================================"
        echo -e "${NC}"
        echo "Run: ./scripts/lint.sh fix"
        echo "Or:  make format"
    fi
    
    exit $EXIT_CODE
}

# Run main function
main "$@"