# Dependency Detection Utilities
# This module provides enhanced dependency detection functions with error handling, logging, caching, and version checking
# It includes support for marker, nemotronparse, and Tesseract OCR dependencies

import importlib
import logging
import subprocess
import sys
from functools import lru_cache
from typing import Dict, Optional, Tuple

# Use centralized logging
from .logging_config import get_logger

logger = get_logger(__name__)

# Try to import metadata for version checking
try:
    import importlib.metadata
    importlib_metadata_available = True
except ImportError:
    importlib_metadata_available = False
    logger.debug("importlib.metadata not available")

class DependencyError(Exception):
    """Custom exception for dependency-related errors."""
    pass

class DependencyVersionError(DependencyError):
    """Custom exception for dependency version mismatches."""
    pass

def _get_installed_version(package_name: str) -> Optional[str]:
    """Get the installed version of a package.
    
    Args:
        package_name: Name of the package to check
        
    Returns:
        Version string if package is installed, None otherwise
        
    Raises:
        DependencyError: If there's a critical error during version detection
    """
    try:
        module = importlib.import_module(package_name)
        if hasattr(module, '__version__'):
            return module.__version__
        elif hasattr(module, 'version'):
            return module.version
        else:
                        # Try to get version from package metadata
                        if importlib_metadata_available:
                            try:
                                return importlib.metadata.version(package_name)
                            except importlib.metadata.PackageNotFoundError as e:
                                logger.debug(f"Package metadata not available for {package_name}: {e}")
                                return None
                            except Exception as e:
                                logger.debug(f"Error getting package metadata for {package_name}: {e}")
                                return None
    except ImportError as e:
        logger.debug(f"Could not determine version for {package_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting version for {package_name}: {e}")
        raise DependencyError(f"Failed to get version for {package_name}: {e}") from e

def _check_version_requirement(package_name: str, required_version: Optional[str] = None) -> bool:
    """Check if installed package meets version requirements.
    
    Args:
        package_name: Name of the package
        required_version: Optional version requirement (e.g., '>=1.0.0')
        
    Returns:
        True if version requirement is met or no requirement specified, False otherwise
        
    Raises:
        DependencyVersionError: If version check fails
    """
    if not required_version:
        return True
         
    try:
        installed_version = _get_installed_version(package_name)
        if not installed_version:
            raise DependencyVersionError(f"{package_name} is installed but version could not be determined")
             
        try:
            import packaging.version
            import packaging.specifiers
            
            version = packaging.version.parse(installed_version)
            specifier = packaging.specifiers.SpecifierSet(required_version)
            
            if version not in specifier:
                raise DependencyVersionError(
                    f"{package_name} version {installed_version} does not satisfy requirement {required_version}"
                )
            
            logger.info(f"Version requirement satisfied: {package_name} {installed_version} meets {required_version}")
            return True
            
        except ImportError:
            logger.warning("packaging library not available, skipping version check")
            return True
        except Exception as e:
            raise DependencyVersionError(f"Version check failed for {package_name}: {e}")
    except DependencyError as e:
        logger.error(f"Dependency error during version check for {package_name}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during version check for {package_name}: {e}")
        raise DependencyVersionError(f"Version check failed for {package_name}: {e}") from e

@lru_cache(maxsize=32)
def has_marker_dependencies(required_version: Optional[str] = None) -> bool:
    """Check if marker optional dependencies are available.
    
    This function checks for the presence of marker-pdf and surya-ocr packages.
    Results are cached to avoid repeated import attempts.
    
    Args:
        required_version: Optional version requirement string (e.g., '>=1.0.0')
        
    Returns:
        True if all required dependencies are available and meet version requirements,
        False otherwise
        
    Logs:
        Debug information about dependency availability
        Warning information about version mismatches
        Error information about critical failures
    """
    dependencies = {
        'marker_pdf': required_version,
        'surya_ocr': required_version
    }
    
    missing_dependencies = []
    version_errors = []
    critical_errors = []
    
    for package_name, version_req in dependencies.items():
        try:
            # Check if package can be imported
            importlib.import_module(package_name)
            logger.debug(f"{package_name} is available")
            
            # Check version if required
            if version_req:
                try:
                    _check_version_requirement(package_name, version_req)
                    logger.debug(f"{package_name} version requirement satisfied")
                except DependencyVersionError as e:
                    version_errors.append(str(e))
                    logger.warning(str(e))
                        
        except ImportError as e:
            missing_dependencies.append(package_name)
            logger.debug(f"{package_name} not available: {e}")
        except Exception as e:
            critical_errors.append(f"{package_name}: {e}")
            logger.error(f"Critical error checking {package_name}: {e}")
    
    # Log summary
    if missing_dependencies:
        logger.warning(f"Missing marker dependencies: {', '.join(missing_dependencies)}")
        logger.warning("Marker PDF processor will be disabled. "
                      "To enable marker functionality, install with: pip install .[marker]")
    
    if version_errors:
        for error in version_errors:
            logger.warning(error)
    
    if critical_errors:
        for error in critical_errors:
            logger.error(f"Critical dependency check error: {error}")
    
    # Return True only if all dependencies are present and versions are compatible
    # Return False if there are critical errors to indicate dependency check failure
    return not missing_dependencies and not version_errors and not critical_errors

@lru_cache(maxsize=32)
def has_nemotronparse_dependencies(required_version: Optional[str] = None) -> bool:
    """Check if nemotronparse optional dependencies are available.

    This function checks for the presence of the openai package.
    Results are cached to avoid repeated import attempts.

    Args:
        required_version: Optional version requirement string (e.g., '>=1.0.0')

    Returns:
        True if all required dependencies are available and meet version requirements,
        False otherwise

    Logs:
        Debug information about dependency availability
        Warning information about version mismatches
        Error information about critical failures
    """
    dependencies = {
        'openai': required_version
    }

    missing_dependencies = []
    version_errors = []
    critical_errors = []

    for package_name, version_req in dependencies.items():
        try:
            # Check if package can be imported
            importlib.import_module(package_name)
            logger.debug(f"{package_name} is available")
            
            # Check version if required
            if version_req:
                try:
                    _check_version_requirement(package_name, version_req)
                    logger.debug(f"{package_name} version requirement satisfied")
                except DependencyVersionError as e:
                    version_errors.append(str(e))
                    logger.warning(str(e))
                         
        except ImportError as e:
            missing_dependencies.append(package_name)
            logger.debug(f"{package_name} not available: {e}")
        except Exception as e:
            critical_errors.append(f"{package_name}: {e}")
            logger.error(f"Critical error checking {package_name}: {e}")

    # Log summary
    if missing_dependencies:
        logger.warning(f"Missing nemotronparse dependencies: {', '.join(missing_dependencies)}")
        logger.warning("Nemotron-parse processor will be disabled. "
                      "To enable nemotronparse functionality, install with: pip install .[nemotronparse]")

    if version_errors:
        for error in version_errors:
            logger.warning(error)

    if critical_errors:
        for error in critical_errors:
            logger.error(f"Critical dependency check error: {error}")

    # Return True only if all dependencies are present and versions are compatible
    # Return False if there are critical errors to indicate dependency check failure
    return not missing_dependencies and not version_errors and not critical_errors




def get_dependency_info() -> Dict[str, Dict[str, str]]:
    """Get detailed information about all optional dependencies.
    
    Returns:
        Dictionary containing dependency information including availability and versions
        
    Raises:
        DependencyError: If there's a critical error during dependency information gathering
    """
    all_dependencies = {
        'marker': ['marker_pdf', 'surya_ocr'],
        'nemotronparse': ['openai'],
        'tesseract': ['pytesseract', 'tesseract_binary']
    }
    
    dependency_info = {}
    
    try:
        for group_name, packages in all_dependencies.items():
            group_info = {}
            for package_name in packages:
                package_info = {
                    'available': False,
                    'version': None,
                    'error': None
                }
                
                try:
                    if package_name == 'tesseract_binary':
                        # Special handling for Tesseract OCR binary
                        from .tesseract_dependencies import _check_tesseract_binary_version
                        tesseract_binary_version = _check_tesseract_binary_version()
                        if tesseract_binary_version:
                            package_info['available'] = True
                            package_info['version'] = tesseract_binary_version
                            logger.debug(f"{package_name} is available for dependency info")
                            logger.debug(f"{package_name} version: {package_info['version']}")
                        else:
                            package_info['error'] = "Tesseract OCR binary not found"
                            logger.debug(f"{package_name} not available")
                    else:
                        # Regular Python package handling
                        module = importlib.import_module(package_name)
                        package_info['available'] = True
                        logger.debug(f"{package_name} is available for dependency info")
                        
                        # Try to get version
                        try:
                            package_info['version'] = _get_installed_version(package_name)
                            logger.debug(f"{package_name} version: {package_info['version']}")
                        except Exception as e:
                            package_info['error'] = f"Version detection failed: {e}"
                            logger.warning(f"Version detection failed for {package_name}: {e}")
                             
                except ImportError as e:
                    package_info['error'] = f"Import failed: {e}"
                    logger.debug(f"Import failed for {package_name}: {e}")
                except Exception as e:
                    package_info['error'] = f"Unexpected error: {e}"
                    logger.error(f"Unexpected error getting info for {package_name}: {e}")
                
                group_info[package_name] = package_info
                
            dependency_info[group_name] = group_info
    except Exception as e:
        logger.error(f"Critical error in get_dependency_info: {e}")
        raise DependencyError(f"Failed to get dependency information: {e}") from e
    
    return dependency_info

def log_dependency_status():
    """Log the current status of all optional dependencies.
    
    This function provides a comprehensive status report of all optional dependencies,
    including installation guidance for missing dependencies.
    
    Raises:
        DependencyError: If there's a critical error during status logging
    """
    try:
        dependency_info = get_dependency_info()
        
        logger.info("Dependency Status:")
        for group_name, packages in dependency_info.items():
            group_status = "Available" if all(p['available'] for p in packages.values()) else "Not Available"
            logger.info(f"  {group_name}: {group_status}")
            
            for package_name, package_info in packages.items():
                if package_info['available']:
                    version_str = f" v{package_info['version']}" if package_info['version'] else ""
                    logger.info(f"    - {package_name}{version_str}")
                else:
                    error_msg = f" ({package_info['error']})" if package_info['error'] else ""
                    logger.info(f"    - {package_name}: Not available{error_msg}")
        
        # Provide installation guidance
        missing_marker = any(not p['available'] for p in dependency_info.get('marker', {}).values())
        missing_nemotronparse = any(not p['available'] for p in dependency_info.get('nemotronparse', {}).values())
        missing_tesseract = any(not p['available'] for p in dependency_info.get('tesseract', {}).values())
        
        if missing_marker or missing_nemotronparse or missing_tesseract:
            logger.warning("\nInstallation guidance:")
            if missing_marker:
                logger.warning("  Marker PDF processor disabled: pip install .[marker]")
            if missing_nemotronparse:
                logger.warning("  Nemotron-parse processor disabled: pip install .[nemotronparse]")
            if missing_tesseract:
                logger.warning("  Tesseract OCR disabled: pip install pytesseract and install Tesseract OCR binary")
                logger.warning("     Tesseract OCR binary: https://github.com/tesseract-ocr/tesseract")
            if missing_marker and missing_nemotronparse:
                logger.warning("  To install marker and nemotronparse: pip install .[marker,nemotronparse]")
            if missing_marker and missing_tesseract:
                logger.warning("  To install marker and Tesseract: pip install .[marker] pytesseract + Tesseract OCR binary")
            if missing_nemotronparse and missing_tesseract:
                logger.warning("  To install nemotronparse and Tesseract: pip install .[nemotronparse] pytesseract + Tesseract OCR binary")
            if missing_marker and missing_nemotronparse and missing_tesseract:
                logger.warning("  To install all optional dependencies: pip install .[marker,nemotronparse] pytesseract + Tesseract OCR binary")
            
    except DependencyError:
        # Re-raise dependency errors
        raise
    except Exception as e:
        logger.error(f"Error logging dependency status: {e}")
        raise DependencyError(f"Failed to log dependency status: {e}") from e


def safe_check_dependency(package_name: str, fallback: bool = True) -> bool:
    """Safely check if a dependency is available with fallback mechanism.
    
    This function provides a safe way to check dependencies that won't crash
    the application if dependency checking fails.
    
    Args:
        package_name: Name of the package to check
        fallback: Whether to use fallback mechanism on error (default: True)
        
    Returns:
        True if dependency is available, False otherwise
        
    Note:
        If fallback is True, this function will return False on any error
        instead of raising an exception.
    """
    try:
        importlib.import_module(package_name)
        logger.debug(f"{package_name} is available (safe check)")
        return True
    except ImportError:
        logger.debug(f"{package_name} not available (safe check)")
        return False
    except Exception as e:
        if fallback:
            logger.error(f"Safe check failed for {package_name}, using fallback: {e}")
            return False
        else:
            logger.error(f"Critical error in safe check for {package_name}: {e}")
            raise DependencyError(f"Safe dependency check failed for {package_name}: {e}") from e


def get_installation_instructions() -> Dict[str, str]:
    """Get installation instructions for missing dependencies.
    
    Returns:
        Dictionary with installation instructions for each dependency group
    """
    # Define standard installation instructions
    standard_instructions = {
        'marker': "pip install .[marker]",
        'nemotronparse': "pip install .[nemotronparse]",
        'tesseract': "pip install pytesseract and install Tesseract OCR binary",
        'marker_nemotronparse': "pip install .[marker,nemotronparse]",
        'nemotronparse_tesseract': "pip install .[nemotronparse] pytesseract and install Tesseract OCR binary",
        'marker_tesseract': "pip install .[marker] pytesseract and install Tesseract OCR binary",
        'all': "pip install .[marker,nemotronparse] pytesseract and install Tesseract OCR binary"
    }
    
    try:
        dependency_info = get_dependency_info()
        
        # Check which dependencies are missing
        marker_missing = any(not p['available'] for p in dependency_info.get('marker', {}).values())
        nemotronparse_missing = any(not p['available'] for p in dependency_info.get('nemotronparse', {}).values())
        tesseract_missing = any(not p['available'] for p in dependency_info.get('tesseract', {}).values())
        
        # Build instructions based on what's missing
        instructions = {}
        
        if marker_missing:
            instructions['marker'] = standard_instructions['marker']
        if nemotronparse_missing:
            instructions['nemotronparse'] = standard_instructions['nemotronparse']
        if tesseract_missing:
            instructions['tesseract'] = standard_instructions['tesseract']
        
        # Add combined instructions only if multiple dependencies are missing
        if marker_missing and nemotronparse_missing:
            instructions['marker_nemotronparse'] = standard_instructions['marker_nemotronparse']
        if marker_missing and tesseract_missing:
            instructions['marker_tesseract'] = standard_instructions['marker_tesseract']
        if nemotronparse_missing and tesseract_missing:
            instructions['nemotronparse_tesseract'] = standard_instructions['nemotronparse_tesseract']
        if marker_missing and nemotronparse_missing and tesseract_missing:
            instructions['all'] = standard_instructions['all']
        
        # Always include basic instructions for completeness (as per original behavior)
        if 'marker' not in instructions:
            instructions['marker'] = standard_instructions['marker']
        if 'nemotronparse' not in instructions:
            instructions['nemotronparse'] = standard_instructions['nemotronparse']
        if 'tesseract' not in instructions:
            instructions['tesseract'] = standard_instructions['tesseract']
        if 'all' not in instructions:
            instructions['all'] = standard_instructions['all']
            
        return instructions
        
    except Exception as e:
        logger.error(f"Error getting installation instructions: {e}")
        # Return standard instructions even on error
        return standard_instructions