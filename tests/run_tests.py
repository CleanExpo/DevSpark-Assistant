"""
Test runner script for DevSpark Assistant
"""
import pytest
import sys
import os

if __name__ == "__main__":
    # Add the parent directory to sys.path to allow tests to import the package
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    # Collect test args
    args = sys.argv[1:] or ["--verbose"]
    
    # Run the tests
    exit_code = pytest.main(args)
    
    # Exit with the pytest exit code
    sys.exit(exit_code) 