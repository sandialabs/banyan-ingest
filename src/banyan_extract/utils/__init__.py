# Utilities module
# This module provides utility functions for the banyan-extract package

from .dependencies import (
    has_marker_dependencies,
    has_nemotronparse_dependencies,
    get_dependency_info,
    log_dependency_status,
    DependencyError,
    DependencyVersionError
)

from .image_rotation import (
    rotate_image,
    is_valid_rotation_angle,
    normalize_rotation_angle
)