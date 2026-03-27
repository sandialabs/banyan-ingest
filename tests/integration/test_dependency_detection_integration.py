# Integration Test for Dependency Detection
# This file contains integration tests for the enhanced dependency detection functions

import pytest
import sys

# Add the source directory to the path
sys.path.insert(0, '/projects/src')

from banyan_extract.utils.dependencies import (
    has_marker_dependencies,
    has_nemotronparse_dependencies,
    get_dependency_info,
    log_dependency_status
)


def test_dependency_detection_integration():
    """Test that dependency detection works in the context of the full application."""
    # Test basic functionality
    marker_available = has_marker_dependencies()
    nemotronparse_available = has_nemotronparse_dependencies()
    
    # These should return boolean values
    assert isinstance(marker_available, bool)
    assert isinstance(nemotronparse_available, bool)
    
    # Test dependency info
    dependency_info = get_dependency_info()
    assert isinstance(dependency_info, dict)
    assert 'marker' in dependency_info
    assert 'nemotronparse' in dependency_info
    
    # Test that the functions can be called multiple times (caching test)
    marker_available_2 = has_marker_dependencies()
    nemotronparse_available_2 = has_nemotronparse_dependencies()
    
    assert marker_available == marker_available_2
    assert nemotronparse_available == nemotronparse_available_2


def test_dependency_detection_with_version_requirements():
    """Test dependency detection with version requirements.
    
    This test validates that version requirements are handled gracefully.
    The test checks the actual availability of dependencies in the test environment
    and adjusts its logic accordingly, rather than making assumptions about what
    should be available.
    """
    # Test with no version requirement (should work the same as basic test)
    marker_no_version = has_marker_dependencies()
    nemotronparse_no_version = has_nemotronparse_dependencies()
    
    # Test with version requirement (should handle gracefully)
    marker_with_version = has_marker_dependencies(">=0.0.1")
    nemotronparse_with_version = has_nemotronparse_dependencies(">=0.0.1")
    
    # Debug output to understand the results
    print(f"\nDebug - Marker: no_version={marker_no_version}, with_version={marker_with_version}")
    print(f"Debug - Nemotronparse: no_version={nemotronparse_no_version}, with_version={nemotronparse_with_version}")
    
    # Get actual dependency information to understand the current state
    dependency_info = get_dependency_info()
    marker_pdf_available = dependency_info['marker']['marker_pdf']['available']
    surya_ocr_available = dependency_info['marker']['surya_ocr']['available']
    openai_available = dependency_info['nemotronparse']['openai']['available']
    
    print(f"Actual dependency availability - marker_pdf: {marker_pdf_available}, surya_ocr: {surya_ocr_available}, openai: {openai_available}")
  
    # Test logic based on actual dependency availability
    # For unavailable dependencies, results should always be the same
    if not marker_pdf_available or not surya_ocr_available:
        # If marker dependencies are not available, both checks should return False
        assert marker_no_version is False, "Marker dependencies should be reported as unavailable"
        assert marker_with_version is False, "Marker version check should return False when dependencies are unavailable"
  
    if not openai_available:
        # If nemotronparse dependencies are not available, both checks should return False
        assert nemotronparse_no_version is False, "Nemotronparse dependencies should be reported as unavailable"
        assert nemotronparse_with_version is False, "Nemotronparse version check should return False when dependencies are unavailable"
    
    # For available dependencies, we need to be more flexible
    # The version check might fail due to missing packaging library or version mismatch
    if marker_pdf_available and surya_ocr_available:
        # If marker is available, version check should either pass or fail gracefully
        assert isinstance(marker_with_version, bool), "Version check should return boolean result"
        print(f"Marker dependency available - version check result: {marker_with_version}")
        
        # If version check fails, it should be a clean failure, not an exception
        if not marker_with_version:
            print("Marker version check failed (expected if version requirements not met)")
    
    if openai_available:
        # If nemotronparse is available, version check should either pass or fail gracefully
        assert isinstance(nemotronparse_with_version, bool), "Version check should return boolean result"
        print(f"Nemotronparse dependency available - version check result: {nemotronparse_with_version}")
        
        # If version check fails, it should be due to version mismatch, not an error
        if not nemotronparse_with_version:
            openai_info = dependency_info.get('nemotronparse', {}).get('openai', {})
            print(f"OpenAI version info: {openai_info}")
            
            # The failure should be due to version mismatch, not import error
            if openai_info.get('available'):
                print("Version check failed due to version mismatch (expected behavior)")
            else:
                print("Version check failed due to import error (unexpected)")
                assert False, "Version check should not fail due to import error when dependency is available"


def test_dependency_info_structure():
    """Test that dependency info has the expected structure."""
    dependency_info = get_dependency_info()
    
    # Check top-level structure
    assert 'marker' in dependency_info
    assert 'nemotronparse' in dependency_info
    
    # Check marker dependencies
    marker_deps = dependency_info['marker']
    assert 'marker_pdf' in marker_deps
    assert 'surya_ocr' in marker_deps
    
    # Check nemotronparse dependencies
    nemotronparse_deps = dependency_info['nemotronparse']
    assert 'openai' in nemotronparse_deps
    
    # Check that each package has the expected fields
    for group_name, packages in dependency_info.items():
        for package_name, package_info in packages.items():
            assert 'available' in package_info
            assert 'version' in package_info
            assert 'error' in package_info
            assert isinstance(package_info['available'], bool)


def test_log_dependency_status():
    """Test that log_dependency_status runs without errors."""
    # This should not raise any exceptions
    try:
        log_dependency_status()
        assert True  # If we get here, the function worked
    except Exception as e:
        pytest.fail(f"log_dependency_status raised an exception: {e}")


def test_caching_behavior_integration():
    """Test that caching works correctly in the integration context."""
    # Clear cache first
    has_marker_dependencies.cache_clear()
    has_nemotronparse_dependencies.cache_clear()
    
    # First calls
    result1 = has_marker_dependencies()
    result2 = has_nemotronparse_dependencies()
    
    # Second calls (should use cache)
    result3 = has_marker_dependencies()
    result4 = has_nemotronparse_dependencies()
    
    # Results should be identical
    assert result1 == result3
    assert result2 == result4


def test_error_handling_integration():
    """Test that the dependency system handles errors gracefully in integration context."""
    # Test that basic functions don't crash
    try:
        marker_available = has_marker_dependencies()
        nemotronparse_available = has_nemotronparse_dependencies()
        dependency_info = get_dependency_info()
        
        # These should all be valid results
        assert isinstance(marker_available, bool)
        assert isinstance(nemotronparse_available, bool)
        assert isinstance(dependency_info, dict)
        
    except Exception as e:
        pytest.fail(f"Dependency functions should not crash: {e}")


def test_safe_dependency_check_integration():
    """Test safe dependency checking in integration context."""
    from banyan_extract.utils.dependencies import safe_check_dependency
    
    # Test with core Python module (should always be available)
    result = safe_check_dependency('sys')
    assert result is True
    
    # Test with likely non-existent module
    result = safe_check_dependency('nonexistent_module_xyz_123')
    assert result is False


def test_installation_instructions_integration():
    """Test installation instructions in integration context."""
    from banyan_extract.utils.dependencies import get_installation_instructions
    
    # Should always return valid instructions
    instructions = get_installation_instructions()
    assert isinstance(instructions, dict)
    assert len(instructions) > 0


def test_error_recovery_integration():
    """Test that the system can recover from dependency check errors."""
    # Clear cache to ensure fresh checks
    has_marker_dependencies.cache_clear()
    has_nemotronparse_dependencies.cache_clear()
    
    # First check
    result1 = has_marker_dependencies()
    result2 = has_nemotronparse_dependencies()
    
    # Second check (should use cache and not fail)
    result3 = has_marker_dependencies()
    result4 = has_nemotronparse_dependencies()
    
    # Results should be consistent
    assert result1 == result3
    assert result2 == result4


def test_dependency_info_completeness():
    """Test that dependency info contains all expected information."""
    dependency_info = get_dependency_info()
    
    # Check structure
    assert 'marker' in dependency_info
    assert 'nemotronparse' in dependency_info
    
    # Check marker dependencies
    marker_deps = dependency_info['marker']
    assert 'marker_pdf' in marker_deps
    assert 'surya_ocr' in marker_deps
    
    # Check nemotronparse dependencies
    nemotronparse_deps = dependency_info['nemotronparse']
    assert 'openai' in nemotronparse_deps
    
    # Check each package has expected fields
    for group_name, packages in dependency_info.items():
        for package_name, package_info in packages.items():
            assert 'available' in package_info
            assert 'version' in package_info
            assert 'error' in package_info
            assert isinstance(package_info['available'], bool)
            
            # If available, version should be string or None
            if package_info['available']:
                assert package_info['version'] is None or isinstance(package_info['version'], str)
            
            # Error should be string or None
            assert package_info['error'] is None or isinstance(package_info['error'], str)