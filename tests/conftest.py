# Test Configuration and Fixtures
# This file contains pytest fixtures and configuration that are shared across all tests

import pytest
import os
import tempfile
from pathlib import Path

# Base directory for test data
TEST_DATA_DIR = Path(__file__).parent / "data"

@pytest.fixture
def test_data_dir():
    """Return the path to the test data directory."""
    return TEST_DATA_DIR

@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_pdf_file(test_data_dir):
    """Return path to a sample PDF file for testing."""
    return test_data_dir / "processors" / "sample.pdf"

@pytest.fixture
def sample_pptx_file(test_data_dir):
    """Return path to a sample PPTX file for testing."""
    return test_data_dir / "processors" / "sample.pptx"

@pytest.fixture
def sample_json_output(test_data_dir):
    """Return path to a sample JSON output file."""
    return test_data_dir / "outputs" / "sample_output.json"

# Add more fixtures as needed for common test scenarios