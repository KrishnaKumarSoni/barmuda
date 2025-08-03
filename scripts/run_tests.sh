#!/bin/bash

# Barmuda Test Runner Script
# Usage: ./scripts/run_tests.sh [critical|important|all|coverage]

set -e  # Exit on any error

echo "🧪 Barmuda Test Suite Runner"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest not found. Installing test dependencies..."
    pip install -r requirements-test.txt
fi

# Set test environment variables
export TESTING=true
export FLASK_SECRET_KEY="test-secret-key"
export OPENAI_API_KEY="test-openai-key"

# Default to running critical tests
TEST_TYPE=${1:-critical}

case $TEST_TYPE in
    "critical")
        print_status "Running CRITICAL tests..."
        pytest tests/critical/ -v --tb=short
        ;;
    "important") 
        print_status "Running IMPORTANT tests..."
        pytest tests/important/ -v --tb=short
        ;;
    "all")
        print_status "Running ALL tests..."
        pytest tests/ -v --tb=short
        ;;
    "coverage")
        print_status "Running tests with coverage..."
        pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
        print_status "Coverage report generated in htmlcov/"
        ;;
    "fast")
        print_status "Running fast test suite..."
        pytest tests/critical/ tests/important/ -x --tb=line
        ;;
    *)
        print_warning "Unknown test type: $TEST_TYPE"
        echo "Usage: $0 [critical|important|all|coverage|fast]"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    print_status "All tests passed! 🎉"
else
    print_error "Some tests failed! 😞"
    exit 1
fi