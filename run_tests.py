#!/usr/bin/env python3
"""
Test runner script for the Google Ads API application.
Provides easy commands to run different types of tests.
"""
import sys
import subprocess
import argparse
import os
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False


def install_test_dependencies():
    """Install test dependencies."""
    return run_command(
        "pip install -r requirements.txt",
        "Installing test dependencies"
    )


def run_unit_tests():
    """Run unit tests only."""
    return run_command(
        "python -m pytest tests/unit/ -v --tb=short --cov=google_ads_server --cov-report=term-missing",
        "Running unit tests"
    )


def run_api_tests():
    """Run API endpoint tests only."""
    return run_command(
        "python -m pytest tests/api/ -v --tb=short --cov=app --cov-report=term-missing",
        "Running API endpoint tests"
    )


def run_integration_tests():
    """Run integration tests only."""
    return run_command(
        "python -m pytest tests/integration/ -v --tb=short",
        "Running integration tests"
    )


def run_all_tests():
    """Run all tests."""
    return run_command(
        "python -m pytest tests/ -v --tb=short --cov=app --cov=google_ads_server --cov-report=term-missing --cov-report=html:htmlcov",
        "Running all tests"
    )


def run_tests_with_coverage():
    """Run all tests with detailed coverage report."""
    return run_command(
        "python -m pytest tests/ -v --cov=app --cov=google_ads_server --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml",
        "Running all tests with coverage report"
    )


def run_specific_test(test_path: str):
    """Run a specific test file or test function."""
    return run_command(
        f"python -m pytest {test_path} -v --tb=short",
        f"Running specific test: {test_path}"
    )


def run_tests_by_marker(marker: str):
    """Run tests by marker."""
    return run_command(
        f"python -m pytest tests/ -m {marker} -v --tb=short",
        f"Running tests with marker: {marker}"
    )


def generate_coverage_report():
    """Generate HTML coverage report."""
    return run_command(
        "python -m pytest tests/ --cov=app --cov=google_ads_server --cov-report=html:htmlcov --cov-report=term-missing",
        "Generating coverage report"
    )


def run_linting():
    """Run code linting."""
    return run_command(
        "python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics",
        "Running code linting"
    )


def run_type_checking():
    """Run type checking."""
    return run_command(
        "python -m mypy . --ignore-missing-imports",
        "Running type checking"
    )


def clean_test_artifacts():
    """Clean test artifacts."""
    artifacts = [
        "htmlcov/",
        ".coverage",
        ".pytest_cache/",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        "*.pyd"
    ]
    
    for artifact in artifacts:
        run_command(
            f"find . -name '{artifact}' -type d -exec rm -rf {{}} + 2>/dev/null || true",
            f"Cleaning {artifact}"
        )
    
    run_command(
        "find . -name '*.pyc' -delete",
        "Cleaning Python cache files"
    )


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="Test runner for Google Ads API application")
    parser.add_argument(
        "command",
        choices=[
            "install", "unit", "api", "integration", "all", "coverage",
            "specific", "marker", "lint", "type-check", "clean", "quick"
        ],
        help="Test command to run"
    )
    parser.add_argument(
        "--test-path",
        help="Specific test path (for 'specific' command)"
    )
    parser.add_argument(
        "--marker",
        help="Test marker (for 'marker' command)"
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Skip dependency installation"
    )
    
    args = parser.parse_args()
    
    # Change to project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    success = True
    
    # Install dependencies unless --no-install is specified
    if not args.no_install and args.command != "install":
        success = install_test_dependencies()
    
    if not success:
        print("\n❌ Failed to install dependencies. Exiting.")
        sys.exit(1)
    
    # Run the specified command
    if args.command == "install":
        success = install_test_dependencies()
    
    elif args.command == "unit":
        success = run_unit_tests()
    
    elif args.command == "api":
        success = run_api_tests()
    
    elif args.command == "integration":
        success = run_integration_tests()
    
    elif args.command == "all":
        success = run_all_tests()
    
    elif args.command == "coverage":
        success = run_tests_with_coverage()
    
    elif args.command == "specific":
        if not args.test_path:
            print("❌ --test-path is required for 'specific' command")
            sys.exit(1)
        success = run_specific_test(args.test_path)
    
    elif args.command == "marker":
        if not args.marker:
            print("❌ --marker is required for 'marker' command")
            sys.exit(1)
        success = run_tests_by_marker(args.marker)
    
    elif args.command == "lint":
        success = run_linting()
    
    elif args.command == "type-check":
        success = run_type_checking()
    
    elif args.command == "clean":
        clean_test_artifacts()
        print("\n✅ Test artifacts cleaned successfully!")
        return
    
    elif args.command == "quick":
        success = run_command(
            "python -m pytest tests/unit/test_google_ads_server.py::TestFormatCustomerId -v",
            "Running quick test (format_customer_id only)"
        )
    
    # Print summary
    if success:
        print(f"\n✅ {args.command} command completed successfully!")
    else:
        print(f"\n❌ {args.command} command failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 