# Tesseract Dependency Detection Utilities
# This module provides Tesseract-specific dependency detection functions

import importlib
import logging
import sys
from functools import lru_cache
from typing import Optional

# Import the version checking function from dependencies module
from .dependencies import _check_version_requirement

# Use centralized logging
from .logging_config import get_logger

logger = get_logger(__name__)

class DependencyError(Exception):
    """Custom exception for dependency-related errors."""
    pass

class DependencyVersionError(DependencyError):
    """Custom exception for dependency version mismatches."""
    pass

def _check_tesseract_binary_version() -> Optional[str]:
    """Check Tesseract OCR binary version using pytesseract.
    
    Returns:
        Tesseract version string if available, None otherwise
        
    Raises:
        DependencyError: If there's a critical error during version detection
    """
    logger.debug("Attempting to check Tesseract OCR binary version using pytesseract")
    
    try:
        # Import pytesseract and get version
        import pytesseract
        pytesseract_version = pytesseract.get_tesseract_version()
        
        if pytesseract_version:
            logger.debug(f"SUCCESS: Tesseract binary verified via pytesseract (version: {pytesseract_version})")
            return pytesseract_version
        else:
            logger.debug("pytesseract.get_tesseract_version() returned None")
            return None
            
    except ImportError:
        logger.debug("pytesseract not available")
        return None
    except pytesseract.TesseractNotFoundError:
        logger.debug("Tesseract binary not found")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error checking Tesseract binary version: {e}")
        logger.warning("This may indicate a configuration issue with pytesseract")
        return None


@lru_cache(maxsize=32)
def has_tesseract_dependencies(pytesseract_version: Optional[str] = None, 
                              tesseract_version: Optional[str] = None) -> bool:
    """Check if Tesseract OCR dependencies are available.
    
    This function checks for both the pytesseract Python package and the Tesseract OCR binary.
    Results are cached to avoid repeated import attempts and system calls.
    
    Args:
        pytesseract_version: Optional version requirement for pytesseract (e.g., '>=0.3.10')
        tesseract_version: Optional version requirement for Tesseract OCR binary (e.g., '>=4.0.0')
        
    Returns:
        True if all required dependencies are available and meet version requirements,
        False otherwise
        
    Logs:
        Debug information about dependency availability
        Warning information about version mismatches
        Error information about critical failures
    """
    missing_dependencies = []
    version_errors = []
    critical_errors = []
    
    # Check pytesseract Python package
    logger.debug("Attempting to import pytesseract Python package")
    try:
        importlib.import_module('pytesseract')
        logger.debug("SUCCESS: pytesseract Python package imported successfully")
        
        # Check pytesseract version if required
        if pytesseract_version:
            logger.debug(f"Checking pytesseract version requirement: {pytesseract_version}")
            try:
                from .dependencies import _check_version_requirement
                _check_version_requirement('pytesseract', pytesseract_version)
                logger.debug("SUCCESS: pytesseract version requirement satisfied")
            except DependencyVersionError as e:
                version_errors.append(str(e))
                logger.warning(f"FAILED: pytesseract version requirement not met: {e}")
                  
    except ImportError as e:
        missing_dependencies.append('pytesseract')
        logger.debug(f"FAILED: pytesseract Python package not available: {e}")
    except Exception as e:
        critical_errors.append(f"pytesseract: {e}")
        logger.error(f"CRITICAL ERROR: Unexpected error checking pytesseract: {e}")
    
    # Check Tesseract OCR binary
    logger.debug("Attempting to check Tesseract OCR binary availability")
    try:
        tesseract_binary_version = _check_tesseract_binary_version()
        if tesseract_binary_version:
            logger.debug(f"SUCCESS: Tesseract OCR binary is available (version: {tesseract_binary_version})")
            
            # Check Tesseract binary version if required
            if tesseract_version:
                logger.debug(f"Checking Tesseract OCR binary version requirement: {tesseract_version}")
                try:
                    # Create a temporary module-like object for version checking
                    class TesseractBinary:
                        __version__ = tesseract_binary_version
                    
                    # Temporarily add to sys.modules for version checking
                    sys.modules['tesseract_binary'] = TesseractBinary()
                    
                    _check_version_requirement('tesseract_binary', tesseract_version)
                    logger.debug("SUCCESS: Tesseract OCR binary version requirement satisfied")
                    
                    # Clean up
                    del sys.modules['tesseract_binary']
                    
                except DependencyVersionError as e:
                    version_errors.append(str(e))
                    logger.warning(f"FAILED: Tesseract OCR binary version requirement not met: {e}")
                except Exception as e:
                    critical_errors.append(f"tesseract_binary version check: {e}")
                    logger.error(f"CRITICAL ERROR: Unexpected error checking Tesseract binary version: {e}")
        else:
            missing_dependencies.append('tesseract_binary')
            logger.debug("FAILED: Tesseract OCR binary not available")
            
    except DependencyError as e:
        critical_errors.append(f"tesseract_binary: {e}")
        logger.error(f"CRITICAL ERROR: Dependency error checking Tesseract binary: {e}")
    except Exception as e:
        critical_errors.append(f"tesseract_binary: {e}")
        logger.error(f"CRITICAL ERROR: Unexpected error checking Tesseract binary: {e}")
    
    # Log final decision about dependency availability
    logger.debug("Evaluating final Tesseract dependency availability decision")
    logger.debug(f"Missing dependencies: {missing_dependencies if missing_dependencies else 'None'}")
    logger.debug(f"Version errors: {version_errors if version_errors else 'None'}")
    logger.debug(f"Critical errors: {critical_errors if critical_errors else 'None'}")
    
    # Log summary
    if missing_dependencies:
        logger.warning(f"Missing Tesseract dependencies: {', '.join(missing_dependencies)}")
        logger.warning("Tesseract OCR functionality will be disabled. "
                      "To enable rotation detection and OCR features, install:")
        logger.warning("  1. pytesseract package: pip install pytesseract")
        logger.warning("  2. Tesseract OCR binary: Download from https://github.com/tesseract-ocr/tesseract")
        logger.warning("     or install via package manager (e.g., 'brew install tesseract' on macOS)")
    
    if version_errors:
        for error in version_errors:
            logger.warning(error)
    
    if critical_errors:
        for error in critical_errors:
            logger.error(f"Critical Tesseract dependency check error: {error}")
    
    # Return True only if all dependencies are present and versions are compatible
    # Return False if there are critical errors to indicate dependency check failure
    final_decision = not missing_dependencies and not version_errors and not critical_errors
    logger.debug(f"FINAL DECISION: Tesseract dependencies available: {final_decision}")
    
    return final_decision