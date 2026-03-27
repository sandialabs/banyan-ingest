# Test Configuration and Fixtures
# This file contains pytest fixtures and configuration that are shared across all tests

import pytest
import os
from pathlib import Path

# Base directory for test data
TEST_DATA_DIR = Path(__file__).parent / "data"

# Import dependency checking functions directly from dependencies.py
from banyan_extract.utils.dependencies import has_marker_dependencies, has_nemotronparse_dependencies

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary directory for test outputs using pytest's tmp_path."""
    return tmp_path

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

def has_all_optional_dependencies():
    """Check if all optional dependencies are available."""
    return has_marker_dependencies() and has_nemotronparse_dependencies()

@pytest.fixture(scope="session")
def marker_available():
    """Fixture that indicates if marker dependencies are available."""
    return has_marker_dependencies()

@pytest.fixture(scope="session")
def nemotronparse_available():
    """Fixture that indicates if nemotronparse dependencies are available."""
    return has_nemotronparse_dependencies()

@pytest.fixture(scope="session")
def all_optional_deps_available():
    """Fixture that indicates if all optional dependencies are available."""
    return has_all_optional_dependencies()

def pytest_addoption(parser):
    """Add custom command-line options for test filtering.
    
    This function adds a command-line option to enable debug logging
    for test filtering decisions.
    """
    parser.addoption(
        "--filter-debug",
        action="store_true",
        default=False,
        help="Enable debug logging for test filtering decisions"
    )


def pytest_configure(config):
    """Register custom pytest markers and configure logging.
    
    These markers are used to categorize tests based on their dependency requirements:
    - requires_marker: Tests that require marker PDF processing dependencies (marker_pdf, surya_ocr)
    - requires_nemotronparse: Tests that require nemotronparse dependencies (openai)
    - core: Tests that only use core functionality and have no optional dependencies
    
    Note: Tests can use both custom markers and automatic filtering. Custom markers
    take precedence over automatic filtering.
    """
    # Enable debug logging if requested
    if config.getoption("--filter-debug"):
        enable_debug_logging()
    
    config.addinivalue_line(
        "markers",
        "requires_marker: mark test as requiring marker dependencies"
    )
    config.addinivalue_line(
        "markers",
        "requires_nemotronparse: mark test as requiring nemotronparse dependencies"
    )
    config.addinivalue_line(
        "markers",
        "core: mark test as core functionality (no optional dependencies)"
    )


def pytest_collection_modifyitems(items, config):
    """Automatically filter tests based on available dependencies and custom markers.
    
    This enhanced function provides more precise filtering by checking both filename
    and path, supports custom markers in addition to automatic filtering, and adds
    debug logging for filtering decisions.
    
    Filtering Logic:
    1. Check for custom markers first (requires_marker, requires_nemotronparse, core)
    2. Apply automatic filtering based on filename and path patterns
    3. Log debug information about filtering decisions
    
    Args:
        items: List of pytest test items
        config: pytest configuration object
    """
    import logging
    import pathlib
    
    # Get logger and configure based on command line option
    logger = logging.getLogger("pytest_filtering")
    
    # Enable debug logging if --filter-debug flag is set
    if config.getoption("--filter-debug"):
        logger.setLevel(logging.DEBUG)
        
        # Add console handler if not already configured
        if not logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
    else:
        logger.setLevel(logging.INFO)
    
    # Check dependency availability
    marker_available = has_marker_dependencies()
    nemotronparse_available = has_nemotronparse_dependencies()
    
    # Log dependency status at the start
    logger.info(f"Test filtering - Marker dependencies available: {marker_available}")
    logger.info(f"Test filtering - Nemotronparse dependencies available: {nemotronparse_available}")
    
    for item in items:
        # Convert fspath to Path object to access path components
        path_obj = pathlib.Path(str(item.fspath))
        
        # Get relative path for better logging
        try:
            relative_path = path_obj.relative_to(Path(__file__).parent)
        except ValueError:
            relative_path = path_obj
        
        # Check for custom markers first (highest priority)
        has_marker_marker = any(marker.name == "requires_marker" for marker in item.iter_markers())
        has_nemotronparse_marker = any(marker.name == "requires_nemotronparse" for marker in item.iter_markers())
        has_core_marker = any(marker.name == "core" for marker in item.iter_markers())
        
        # Log marker information
        markers_list = [marker.name for marker in item.iter_markers()]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Test: {relative_path}::{item.name} - Markers: {markers_list}")
        
        # Apply filtering based on custom markers
        if has_marker_marker and not marker_available:
            logger.info(f"Skipping (marker marker): {relative_path}::{item.name}")
            item.add_marker(pytest.mark.skip(reason="marker dependencies not available (custom marker)"))
            continue
            
        if has_nemotronparse_marker and not nemotronparse_available:
            logger.info(f"Skipping (nemotronparse marker): {relative_path}::{item.name}")
            item.add_marker(pytest.mark.skip(reason="nemotronparse dependencies not available (custom marker)"))
            continue
        
        # Apply automatic filtering based on filename and path patterns
        # More precise pattern matching
        file_stem = path_obj.stem.lower()
        file_name = path_obj.name.lower()
        file_path_str = str(path_obj).lower()
        
        # Check for marker-related patterns
        marker_patterns = [
            "marker" in file_stem,
            "marker" in file_name,
            "marker" in file_path_str,
            "marker_" in file_stem,
            "_marker" in file_stem
        ]
        
        # Check for nemotronparse-related patterns
        nemotronparse_patterns = [
            "nemotronparse" in file_stem,
            "nemotronparse" in file_name,
            "nemotronparse" in file_path_str,
            "nemotron_" in file_stem,
            "_nemotron" in file_stem
        ]
        
        # Apply automatic filtering
        if any(marker_patterns) and not marker_available and not has_marker_marker:
            logger.info(f"Skipping (auto marker): {relative_path}::{item.name}")
            item.add_marker(pytest.mark.skip(reason="marker dependencies not available (auto-detected)"))
            continue
            
        if any(nemotronparse_patterns) and not nemotronparse_available and not has_nemotronparse_marker:
            logger.info(f"Skipping (auto nemotronparse): {relative_path}::{item.name}")
            item.add_marker(pytest.mark.skip(reason="nemotronparse dependencies not available (auto-detected)"))
            continue
        
        # Log tests that will be run
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Running: {relative_path}::{item.name}")


def enable_debug_logging():
    """Enable debug logging for test filtering.
    
    This function configures logging to show detailed debug information
    about test filtering decisions. It should be called when verbose
    logging is desired.
    
    Returns:
        Configured logger instance
    """
    import logging
    
    logger = logging.getLogger("pytest_filtering")
    logger.setLevel(logging.DEBUG)
    
    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(ch)
    
    return logger


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add enhanced user-friendly terminal summary with comprehensive dependency and test information.
    
    This enhanced summary provides:
    1. Visual indicators (OK/FAIL) for available/missing dependencies
    2. Detailed package breakdown showing individual package status
    3. Version information for installed packages
    4. Comprehensive test execution statistics
    5. Actionable installation guidance with comments
    6. Helpful tips for advanced usage
    7. Better organization with clear section headers
    """
    # Clear caches to ensure we get fresh results (in case tests mocked the imports)
    try:
        has_marker_dependencies.cache_clear()
    except Exception:
        pass
    
    try:
        has_nemotronparse_dependencies.cache_clear()
    except Exception:
        pass
    
    # Import additional utilities for enhanced summary
    from banyan_extract.utils.dependencies import get_dependency_info, get_installation_instructions
    
    # Get comprehensive test statistics
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    xfailed = len(terminalreporter.stats.get('xfailed', []))
    xpassed = len(terminalreporter.stats.get('xpassed', []))
    error = len(terminalreporter.stats.get('error', []))
    
    # Calculate total tests (passed + failed + skipped + xfailed + xpassed + error)
    total_tests = passed + failed + skipped + xfailed + xpassed + error
    
    # Calculate success rate
    success_rate = (passed / total_tests * 100) if total_tests > 0 else 100
    
    # Get detailed dependency information
    dependency_info = get_dependency_info()
    installation_instructions = get_installation_instructions()
    
    # Write enhanced terminal summary
    terminalreporter.write_sep("=", "Test Execution Summary")
    
    # Test statistics section
    terminalreporter.write_line("Test Statistics:")
    terminalreporter.write_line(f"  Total: {total_tests}")
    terminalreporter.write_line(f"  Passed: {passed} [OK]")
    terminalreporter.write_line(f"  Failed: {failed} [FAIL]")
    terminalreporter.write_line(f"  Skipped: {skipped} [SKIP]")
    terminalreporter.write_line(f"  Expected failures: {xfailed}")
    terminalreporter.write_line(f"  Unexpected passes: {xpassed}")
    terminalreporter.write_line(f"  Errors: {error} [ERROR]")
    terminalreporter.write_line(f"  Success rate: {success_rate:.1f}%")
    
    # Add visual indicator based on test results
    if failed == 0 and error == 0:
        terminalreporter.write_line("  Overall: All tests passed! [SUCCESS]")
    elif failed > 0:
        terminalreporter.write_line("  Overall: Some tests failed [FAIL]")
    elif error > 0:
        terminalreporter.write_line("  Overall: Tests completed with errors [ERROR]")
    
    terminalreporter.write_line("")
    
    # Dependency availability section with visual indicators
    terminalreporter.write_sep("=", "Dependency Availability")
    
    # Marker dependencies
    marker_available = has_marker_dependencies()
    marker_status = "[OK] Available" if marker_available else "[FAIL] Not Available"
    terminalreporter.write_line(f"Marker dependencies: {marker_status}")
    
    # Detailed marker package breakdown
    if 'marker' in dependency_info:
        for package_name, package_info in dependency_info['marker'].items():
            if package_info['available']:
                version_str = f" v{package_info['version']}" if package_info['version'] else ""
                terminalreporter.write_line(f"  [OK] {package_name}{version_str}")
            else:
                error_msg = f" ({package_info['error']})" if package_info['error'] else ""
                terminalreporter.write_line(f"  [FAIL] {package_name}: Not available{error_msg}")
    
    # Nemotronparse dependencies
    nemotronparse_available = has_nemotronparse_dependencies()
    nemotronparse_status = "[OK] Available" if nemotronparse_available else "[FAIL] Not Available"
    terminalreporter.write_line(f"Nemotronparse dependencies: {nemotronparse_status}")
    
    # Detailed nemotronparse package breakdown
    if 'nemotronparse' in dependency_info:
        for package_name, package_info in dependency_info['nemotronparse'].items():
            if package_info['available']:
                version_str = f" v{package_info['version']}" if package_info['version'] else ""
                terminalreporter.write_line(f"  [OK] {package_name}{version_str}")
            else:
                error_msg = f" ({package_info['error']})" if package_info['error'] else ""
                terminalreporter.write_line(f"  [FAIL] {package_name}: Not available{error_msg}")
    
    terminalreporter.write_line("")
    
    # Installation guidance section
    terminalreporter.write_sep("=", "Installation Guidance")
    
    # Provide actionable installation guidance with comments
    if not marker_available or not nemotronparse_available:
        terminalreporter.write_line("To install missing dependencies:")
        
        if not marker_available:
            terminalreporter.write_line(f"  # Marker dependencies (PDF processing)")
            terminalreporter.write_line(f"  {installation_instructions['marker']}")
            terminalreporter.write_line(f"  # Includes: marker_pdf, surya_ocr")
            
        if not nemotronparse_available:
            terminalreporter.write_line(f"  # Nemotronparse dependencies (AI parsing)")
            terminalreporter.write_line(f"  {installation_instructions['nemotronparse']}")
            terminalreporter.write_line(f"  # Includes: openai")
            
        if not marker_available and not nemotronparse_available:
            terminalreporter.write_line(f"  # Install all optional dependencies")
            terminalreporter.write_line(f"  {installation_instructions['all']}")
    else:
        terminalreporter.write_line("[OK] All optional dependencies are installed!")
        terminalreporter.write_line("You can run all test suites without restrictions.")
    
    terminalreporter.write_line("")
    
    # Helpful tips section
    terminalreporter.write_sep("=", "Helpful Tips")
    
    if failed > 0 or error > 0:
        terminalreporter.write_line("Troubleshooting:")
        terminalreporter.write_line("  * Check test logs for detailed error messages")
        terminalreporter.write_line("  * Run specific tests with: pytest tests/path/to/test.py")
        terminalreporter.write_line("  * Use verbose mode: pytest -v")
        terminalreporter.write_line("  * Enable debug logging: pytest --filter-debug")
    
    if skipped > 0:
        terminalreporter.write_line("Skipped tests:")
        terminalreporter.write_line("  * Some tests were skipped due to missing dependencies")
        terminalreporter.write_line("  * Install missing dependencies to run all tests")
        terminalreporter.write_line("  * Use markers to control test execution:")
        terminalreporter.write_line("    @pytest.mark.requires_marker")
        terminalreporter.write_line("    @pytest.mark.requires_nemotronparse")
    
    terminalreporter.write_line("Advanced usage:")
    terminalreporter.write_line("  * Run tests with coverage: pytest --cov=src/banyan_extract")
    terminalreporter.write_line("  * Run specific test groups: pytest -m marker")
    terminalreporter.write_line("  * Generate HTML report: pytest --html=report.html")
    terminalreporter.write_line("  * Run only core tests: pytest -m core")
    
    terminalreporter.write_line("")
    
    # Summary footer
    terminalreporter.write_sep("=", "Summary")
    
    if failed == 0 and error == 0:
        terminalreporter.write_line("[SUCCESS] All tests completed successfully!")
        terminalreporter.write_line("Your environment is properly configured.")
    else:
        terminalreporter.write_line("[ERROR] Some tests failed or had errors")
        terminalreporter.write_line("Check the detailed output above for troubleshooting guidance.")
    
    terminalreporter.write_line("Thank you for using banyan-extract!")

# Add more fixtures as needed for common test scenarios
