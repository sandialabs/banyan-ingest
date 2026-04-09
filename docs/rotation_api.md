# Banyan Extract Rotation API Documentation

This document provides comprehensive API documentation for the rotation detection feature in Banyan Extract.

## Table of Contents

1. [Rotation Detection Utilities](#rotation-detection-utilities)
2. [Rotation Feature Details](#rotation-feature-details)
3. [Tesseract OCR Integration](#tesseract-ocr-integration)
4. [Best Practices for Rotation Detection](#best-practices-for-rotation-detection)

## Rotation Detection Utilities

### Overview

The rotation detection utilities provide comprehensive Tesseract OCR-based rotation detection using OSD (Orientation and Script Detection). These utilities are located in `banyan_extract.utils.rotation_detection`.

### Exception Classes

#### `RotationDetectionError`

**Location**: `banyan_extract.utils.rotation_detection.RotationDetectionError`

**Description**: Base exception class for all rotation detection errors.

**Inherits**: `Exception`

#### `TesseractNotFoundError`

**Location**: `banyan_extract.utils.rotation_detection.TesseractNotFoundError`

**Description**: Exception raised when Tesseract OCR is not found or not properly installed.

**Inherits**: `RotationDetectionError`

#### `InvalidImageError`

**Location**: `banyan_extract.utils.rotation_detection.InvalidImageError`

**Description**: Exception raised when an invalid image is provided for rotation detection.

**Inherits**: `RotationDetectionError`

### Core Functions

#### `detect_rotation_angle(image, confidence_threshold=0.7, pytesseract_config=None)`

**Location**: `banyan_extract.utils.rotation_detection.detect_rotation_angle`

**Description**: Detect rotation angle using Tesseract OSD with comprehensive error handling and validation.

**Parameters**:
- `image` (PIL.Image): PIL Image object to analyze for rotation
- `confidence_threshold` (float): Minimum confidence required for rotation detection (0.0 to 1.0, default: 0.7)
- `pytesseract_config` (str): Optional Tesseract configuration string (default: '--psm 0')

**Returns**: Detected rotation angle in degrees (0, 90, 180, 270), or 0.0 if detection fails

**Raises**:
- `InvalidImageError`: If image is None or not a PIL Image object
- `TesseractNotFoundError`: If Tesseract dependencies are not available
- `RotationDetectionError`: If rotation detection fails unexpectedly

**Features**:
- Automatic dependency checking using `has_tesseract_dependencies()`
- Image validation and preprocessing for optimal OSD performance
- RGB conversion with RGBA handling and transparency support
- Memory warnings for large RGBA images (>1M pixels)
- Comprehensive logging at debug, info, and warning levels
- Performance timing for Tesseract operations
- Angle normalization to standard range (0-360°)
- Confidence threshold validation and normalization

**Example Usage**:

```python
from PIL import Image
from banyan_extract.utils.rotation_detection import detect_rotation_angle

image = Image.open('document.jpg')
try:
    angle = detect_rotation_angle(image, confidence_threshold=0.7)
    if angle != 0:
        print(f"Detected rotation: {angle} degrees")
except Exception as e:
    print(f"Rotation detection failed: {e}")
```

#### `detect_rotation_angle_with_fallback(image, confidence_threshold=0.7, pytesseract_config=None)`

**Location**: `banyan_extract.utils.rotation_detection.detect_rotation_angle_with_fallback`

**Description**: Detect rotation angle with automatic fallback to 0 degrees on any error. This is a convenience function that wraps `detect_rotation_angle()` and handles all exceptions gracefully.

**Parameters**:
- `image` (PIL.Image): PIL Image object to analyze for rotation
- `confidence_threshold` (float): Minimum confidence required for rotation detection (0.0 to 1.0, default: 0.7)
- `pytesseract_config` (str): Optional Tesseract configuration string

**Returns**: Detected rotation angle in degrees, or 0.0 on any error

**Features**:
- Never raises exceptions - always returns a numeric value
- Automatic fallback to 0 degrees on any error
- Comprehensive error logging for debugging
- Suitable for production environments where stability is critical
- Maintains all the features of `detect_rotation_angle()`

**Example Usage**:

```python
from PIL import Image
from banyan_extract.utils.rotation_detection import detect_rotation_angle_with_fallback

image = Image.open('document.jpg')
# This will never raise an exception
angle = detect_rotation_angle_with_fallback(image)
print(f"Rotation angle (with fallback): {angle} degrees")
```

#### `get_rotation_correction_info(image, confidence_threshold=0.7, pytesseract_config=None)`

**Location**: `banyan_extract.utils.rotation_detection.get_rotation_correction_info`

**Description**: Get detailed rotation correction information for debugging and logging purposes.

**Parameters**:
- `image` (PIL.Image): PIL Image object to analyze for rotation
- `confidence_threshold` (float): Minimum confidence required for rotation detection (0.0 to 1.0, default: 0.7)
- `pytesseract_config` (str): Optional Tesseract configuration string

**Returns**: Dictionary containing detailed rotation information:

```python
{
    'angle': float,           # Detected rotation angle in degrees
    'confidence': float,      # Detection confidence (0.0 to 1.0)
    'needs_correction': bool, # Whether correction is needed
    'method': str,            # Rotation detection method used
    'success': bool           # Whether detection succeeded
}
```

**Features**:
- Detailed debugging information for troubleshooting
- Success/failure indicators for monitoring
- Method tracking for analytics
- Confidence reporting for quality assessment
- Automatic fallback handling

**Example Usage**:

```python
from PIL import Image
from banyan_extract.utils.rotation_detection import get_rotation_correction_info

image = Image.open('document.jpg')
info = get_rotation_correction_info(image)
print(f"Rotation info: {info}")
```

### Internal Utility Functions

#### `_validate_image(image)`

**Description**: Validate that the input is a valid PIL Image object.

**Parameters**:
- `image`: PIL Image object to validate

**Raises**: `InvalidImageError` if image is None or not a PIL Image object

#### `_preprocess_image_for_osd(image)`

**Description**: Preprocess image for optimal OSD performance.

**Features**:
- Converts images to RGB format for optimal OSD performance
- Handles RGBA images with transparency support
- Provides memory warnings for large RGBA images
- Preserves image quality during conversion

#### `_parse_osd_output(osd_output)`

**Description**: Parse Tesseract OSD output to extract rotation angle and confidence.

**Features**:
- Extracts orientation angle from OSD output
- Handles missing or invalid fields gracefully
- Normalizes confidence to 0.0-1.0 range
- Provides detailed error messages

## Rotation Feature Details

### Implementation Approach

The rotation feature has been implemented as a preprocessing step in the processing pipeline:

1. **Method Parameters**: Rotation angle is passed as a parameter to `process_document()` and `process_batch_documents()` methods
2. **Preprocessing Pipeline**: Rotation is applied to images before OCR processing
3. **Backward Compatibility**: Rotation parameter defaults to 0, maintaining existing behavior
4. **Validation**: Uses utility functions for angle validation and normalization
5. **Auto-Detection**: Uses Tesseract OSD for automatic rotation detection
6. **Confidence Threshold**: Configurable confidence threshold for reliable results

### Current Implementation Status

**NemoparseProcessor**: ✅ Fully implemented
- Rotation is applied as preprocessing before OCR
- Uses `rotate_image` utility function
- Supports all rotation angles
- Validates and normalizes angles
- Automatic rotation detection using Tesseract OSD
- Configurable confidence threshold support
- Comprehensive error handling and fallback mechanisms

**MarkerProcessor**: ⚠️ Not yet implemented
- Shows warning when rotation is specified
- Continues processing without rotation
- Future implementation planned

**PptxProcessor**: ⚠️ Not yet implemented
- Shows warning when rotation is specified
- Continues processing without rotation
- Future implementation planned

**PaperMageProcessor**: ⚠️ Not yet implemented
- Shows warning when rotation is specified
- Continues processing without rotation
- Future implementation planned

### Mathematical Foundation

The rotation feature uses the `rotate_image` utility function from `banyan_extract.utils.image_rotation` which implements:

1. **Rotation Matrix**: Standard 2D rotation mathematics
2. **Optimized Paths**: Uses PIL's `transpose()` for 90/180/270 degree rotations
3. **General Rotation**: Uses PIL's `rotate()` with `expand=True` for other angles
4. **Angle Normalization**: Normalizes angles to [0, 360) range

The rotation detection uses Tesseract OCR's OSD (Orientation and Script Detection) which implements:

1. **OSD Algorithm**: Tesseract's orientation detection based on text line analysis
2. **Confidence Scoring**: Statistical confidence measurement for detection reliability
3. **Page Segmentation**: Automatic page segmentation mode (--psm 0) for optimal results
4. **Script Detection**: Combined orientation and script detection for improved accuracy

### Performance Considerations

- **Memory**: Rotated images with expansion consume more memory
- **CPU**: Rotation operations are CPU-intensive, especially for large images
- **Batch Processing**: Memory usage scales with batch size when using rotation
- **Optimization**: 90/180/270 degree rotations are optimized for better performance
- **Tesseract OSD**: OSD processing adds overhead but provides reliable detection
- **RGBA Conversion**: Large RGBA images may consume significant memory during conversion

### Accuracy Considerations

- **Standard Angles**: 90, 180, 270 degree rotations maintain good OCR accuracy
- **Oblique Angles**: Other angles may slightly reduce OCR accuracy
- **Image Quality**: Rotation uses bicubic resampling by default for quality preservation
- **OSD Reliability**: Tesseract OSD works best with documents containing readable text
- **Confidence Threshold**: Higher thresholds improve reliability but may miss some rotations
- **Document Content**: Documents with clear text patterns provide more reliable detection

### Best Practices for Rotation

1. **Use Standard Angles**: Prefer 90, 180, 270 degrees for best performance and accuracy
2. **Test First**: Always test rotation on sample documents
3. **Monitor Resources**: Watch memory usage with large batches
4. **Backward Compatibility**: Rotation parameter is optional and defaults to 0
5. **Validation**: Use `draw_bboxes=True` to verify processing results

### Best Practices for Rotation Detection

1. **Install Dependencies**: Ensure Tesseract OCR and pytesseract are properly installed
2. **Verify Installation**: Test Tesseract installation with `pytesseract.get_tesseract_version()`
3. **Use Appropriate Thresholds**: Start with default confidence threshold (0.7) and adjust as needed
4. **Check Document Content**: Ensure documents contain readable text for reliable OSD detection
5. **Monitor Performance**: Be aware of performance overhead with auto-detection
6. **Handle Large Images**: Be cautious with large RGBA images due to memory requirements
7. **Use Fallback Mechanism**: Use `detect_rotation_angle_with_fallback()` for production stability
8. **Enable Debug Logging**: Use debug logging for troubleshooting rotation detection issues
9. **Test with Sample Documents**: Validate rotation detection on representative sample documents
10. **Monitor Memory Usage**: Watch memory consumption during batch processing with rotation detection

## Tesseract OCR Integration

### Installation Requirements

For automatic rotation detection, Tesseract OCR and pytesseract are required:

```bash
# Install pytesseract package
pip install pytesseract

# Install Tesseract OCR binary
# Linux (Ubuntu/Debian):
sudo apt install tesseract-ocr

# Linux (Fedora/RHEL):
sudo dnf install tesseract

# macOS:
brew install tesseract

# Windows:
# Download from https://github.com/tesseract-ocr/tesseract
```

### Dependency Checking

The system automatically checks for Tesseract dependencies using:

```python
from banyan_extract.utils.tesseract_dependencies import has_tesseract_dependencies

if has_tesseract_dependencies():
    print("Tesseract OCR is available")
else:
    print("Tesseract OCR is not available")
```

### Verification

Verify Tesseract installation:

```python
import pytesseract
print(pytesseract.get_tesseract_version())
```

### Configuration

Tesseract configuration options for rotation detection:

- `--psm 0`: Automatic page segmentation mode (default)
- `--psm 1`: Automatic segmentation with OSD
- `--psm 3`: Fully automatic segmentation
- Custom configurations can be passed via `pytesseract_config` parameter

### Error Handling

Comprehensive error handling includes:

- `TesseractNotFoundError`: When Tesseract binary is not found
- `ImportError`: When pytesseract package is not installed
- `RotationDetectionError`: For general rotation detection failures
- Automatic fallback to 0 degrees when dependencies are missing
- Detailed logging at debug, info, and warning levels

### Performance Optimization

For optimal performance:

- Use standard rotation angles (90, 180, 270)
- Process documents individually for large files
- Monitor memory usage with large RGBA images
- Use appropriate confidence thresholds
- Enable checkpointing for batch processing

## Cross-References

For processor-specific API details, see:
- [Processor API documentation](processor_api.md)

For troubleshooting information, see:
- [Troubleshooting documentation](troubleshooting.md)

For CLI integration details, see:
- [CLI Integration documentation](cli_integration.md)