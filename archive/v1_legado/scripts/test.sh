#!/bin/bash
# ======================================
# 🧪 TEST SCRIPT - SISTEMA APRENDER
# Comprehensive Testing Suite
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
TEST_TYPE="${1:-all}"
COVERAGE_THRESHOLD=80
REPORT_DIR="test_reports"

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "🧪 Sistema Aprender - Test Suite"
    echo "========================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[TEST]${NC} $1"
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

# Create report directory
setup_reports() {
    mkdir -p $REPORT_DIR
    echo "Test reports will be saved to: $REPORT_DIR"
}

# Unit tests
run_unit_tests() {
    print_step "Running unit tests..."
    
    # Core models tests
    print_step "Testing core models..."
    python manage.py test core.tests.test_models --verbosity=2 || {
        print_error "Core models tests failed"
        return 1
    }
    
    # Core views tests
    print_step "Testing core views..."
    python manage.py test core.tests.test_views --verbosity=2 || {
        print_error "Core views tests failed"
        return 1
    }
    
    # Core forms tests
    print_step "Testing core forms..."
    python manage.py test core.tests.test_forms --verbosity=2 || {
        print_warning "Core forms tests failed (non-critical)"
    }
    
    # API tests
    if [ -d "api/tests" ]; then
        print_step "Testing API endpoints..."
        python manage.py test api.tests --verbosity=2 || {
            print_error "API tests failed"
            return 1
        }
    fi
    
    print_success "Unit tests completed"
}

# Integration tests
run_integration_tests() {
    print_step "Running integration tests..."
    
    # Google Calendar integration
    print_step "Testing Google Calendar integration..."
    python manage.py test core.tests.test_google_calendar --verbosity=2 || {
        print_warning "Google Calendar tests failed (check credentials)"
    }
    
    # Database integration tests
    print_step "Testing database operations..."
    python manage.py test core.tests.test_integration --verbosity=2 || {
        print_error "Integration tests failed"
        return 1
    }
    
    print_success "Integration tests completed"
}

# End-to-end tests
run_e2e_tests() {
    if command -v playwright >/dev/null 2>&1; then
        print_step "Running end-to-end tests..."
        
        # Start test server
        python manage.py runserver --settings=aprender_sistema.settings_test 8001 &
        SERVER_PID=$!
        
        # Wait for server to start
        sleep 5
        
        # Run Playwright tests
        pytest tests/e2e/ -v --html=$REPORT_DIR/e2e_report.html --self-contained-html || {
            print_error "E2E tests failed"
            kill $SERVER_PID
            return 1
        }
        
        # Stop test server
        kill $SERVER_PID
        
        print_success "E2E tests completed"
    else
        print_warning "Playwright not installed - skipping E2E tests"
    fi
}

# Coverage tests
run_coverage_tests() {
    print_step "Running tests with coverage analysis..."
    
    # Run coverage
    coverage run --source='.' manage.py test --verbosity=1
    coverage report --show-missing
    coverage html -d $REPORT_DIR/coverage_html
    coverage xml -o $REPORT_DIR/coverage.xml
    
    # Check coverage threshold
    COVERAGE_PERCENT=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
    
    if [ "${COVERAGE_PERCENT%.*}" -ge $COVERAGE_THRESHOLD ]; then
        print_success "Coverage: $COVERAGE_PERCENT% (meets $COVERAGE_THRESHOLD% threshold)"
    else
        print_error "Coverage: $COVERAGE_PERCENT% (below $COVERAGE_THRESHOLD% threshold)"
        return 1
    fi
    
    echo "Coverage report available at: $REPORT_DIR/coverage_html/index.html"
}

# Performance tests
run_performance_tests() {
    print_step "Running performance tests..."
    
    if command -v locust >/dev/null 2>&1; then
        # Create simple locust test
        cat > $REPORT_DIR/locustfile.py << 'EOF'
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def index_page(self):
        self.client.get("/")
    
    @task
    def health_check(self):
        self.client.get("/health/")
    
    @task(3)
    def admin_login(self):
        self.client.get("/admin/login/")
EOF
        
        # Run locust in headless mode
        cd $REPORT_DIR
        locust -f locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 2 --run-time 30s --html performance_report.html --headless || {
            print_warning "Performance tests failed (server may not be running)"
        }
        cd ..
        
        print_success "Performance tests completed"
    else
        print_warning "Locust not installed - skipping performance tests"
    fi
}

# Security tests
run_security_tests() {
    print_step "Running security tests..."
    
    # Bandit security scan
    print_step "Running Bandit security scan..."
    bandit -r . -x "/venv/,/tests/,/migrations/" -f json -o $REPORT_DIR/bandit_report.json || {
        print_warning "Bandit found security issues - check report"
    }
    
    # Safety dependency check
    print_step "Checking dependencies for vulnerabilities..."
    safety check --json --output $REPORT_DIR/safety_report.json || {
        print_warning "Vulnerable dependencies found - check report"
    }
    
    # Django security check
    print_step "Running Django security checks..."
    python manage.py check --deploy > $REPORT_DIR/django_security.txt 2>&1 || {
        print_warning "Django security issues found - check report"
    }
    
    print_success "Security tests completed"
}

# Cleanup test data
cleanup_test_data() {
    print_step "Cleaning up test data..."
    
    # Remove test database if exists
    if [ -f "test_db.sqlite3" ]; then
        rm test_db.sqlite3
    fi
    
    # Clean up temporary files
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    print_success "Cleanup completed"
}

# Generate test summary
generate_summary() {
    print_step "Generating test summary..."
    
    SUMMARY_FILE="$REPORT_DIR/test_summary.txt"
    
    cat > $SUMMARY_FILE << EOF
Sistema Aprender - Test Summary
===============================
Date: $(date)
Test Type: $TEST_TYPE
Environment: $(python --version)

Test Reports:
- Coverage HTML: coverage_html/index.html
- Coverage XML: coverage.xml
- E2E Report: e2e_report.html
- Performance: performance_report.html
- Security (Bandit): bandit_report.json
- Security (Safety): safety_report.json
- Django Security: django_security.txt

Next Steps:
1. Review coverage report for uncovered code
2. Check security reports for vulnerabilities
3. Address any failed tests
4. Update test documentation if needed
EOF
    
    echo "Test summary saved to: $SUMMARY_FILE"
}

# Show help
show_help() {
    echo "Usage: ./scripts/test.sh [TYPE]"
    echo ""
    echo "Test Types:"
    echo "  all          - Run all tests (default)"
    echo "  unit         - Run unit tests only"
    echo "  integration  - Run integration tests only"
    echo "  e2e          - Run end-to-end tests only"
    echo "  coverage     - Run tests with coverage"
    echo "  performance  - Run performance tests"
    echo "  security     - Run security tests"
    echo "  quick        - Run quick test suite"
    echo ""
    echo "Examples:"
    echo "  ./scripts/test.sh"
    echo "  ./scripts/test.sh unit"
    echo "  ./scripts/test.sh coverage"
}

# Main function
main() {
    case "$TEST_TYPE" in
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
        "unit")
            print_header
            setup_reports
            run_unit_tests
            cleanup_test_data
            ;;
        "integration")
            print_header
            setup_reports
            run_integration_tests
            cleanup_test_data
            ;;
        "e2e")
            print_header
            setup_reports
            run_e2e_tests
            cleanup_test_data
            ;;
        "coverage")
            print_header
            setup_reports
            run_coverage_tests
            cleanup_test_data
            ;;
        "performance")
            print_header
            setup_reports
            run_performance_tests
            cleanup_test_data
            ;;
        "security")
            print_header
            setup_reports
            run_security_tests
            cleanup_test_data
            ;;
        "quick")
            print_header
            setup_reports
            run_unit_tests
            cleanup_test_data
            ;;
        "all"|*)
            print_header
            setup_reports
            run_unit_tests
            run_integration_tests
            run_e2e_tests
            run_coverage_tests
            run_performance_tests
            run_security_tests
            generate_summary
            cleanup_test_data
            ;;
    esac
    
    echo -e "${GREEN}"
    echo "========================================"
    echo "🎉 Test suite completed!"
    echo "========================================"
    echo -e "${NC}"
    echo "Reports available in: $REPORT_DIR"
}

# Check if Django is available
if ! python -c "import django" 2>/dev/null; then
    print_error "Django not found. Please activate your virtual environment."
    exit 1
fi

# Run main function
main "$@"