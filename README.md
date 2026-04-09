# Banyan Extract

`banyan_extract` is a python module that prepares documents for use in GenAI and LLM applications. 

Rather than re-invent the wheel, `banyan_extract` aims to utilize state-of-the-art tools to provide this capability. 


## Installation

### From PyPI (recommended)

In a Python environment (`conda`, `venv`, etc.), use the following:

```bash
cd PATH_TO_REPO/
pip install banyan-extract
```

### From source
```bash
git clone https://github.com/sandialabs/banyan-ingest.git
cd banyan-ingest/
pip install .
```

### Additional Dependecies

You will need poppler installed. 

For **rotation detection** functionality, you need Tesseract OCR (version 4.0 or higher recommended):

```bash
pip install pytesseract
```

Then install the Tesseract OCR binary:
- **Linux** (Ubuntu/Debian): `sudo apt install tesseract-ocr`
- **Linux** (Fedora/RHEL): `sudo dnf install tesseract`
- **macOS**: `brew install tesseract`
- **Windows**: Download from [Tesseract GitHub](https://github.com/tesseract-ocr/tesseract)

**Note**: Tesseract OCR is only required for automatic rotation detection. Manual rotation works without Tesseract.

**Verify Installation**: After installing, verify Tesseract is working:

```python
import pytesseract
print(pytesseract.get_tesseract_version())
```

### OCR Backend Dependencies

The default OCR backend for PPTX processing is now **Nemotron** (changed from Surya).

To use Nemotron OCR (default):
```bash
pip install .[nemotronparse]
```

To use Surya OCR:
```bash
pip install .[marker]
```


## Supported Tools and File Formats
Currently we provide support for `marker` ([link here](https://github.com/datalab-to/marker)) and NVIDIA's `nemotron-parse` models ([link here](https://build.nvidia.com/nvidia/nemotron-parse)).

To install the necessary dependencies for these tools please use `pip install .[marker]` or `pip install .[nemotronparse]` respectively.

**Default OCR Backend**: Nemotron is now the default OCR backend for PPTX processing (changed from Surya).

Note: please ensure you follow the guidelines and usage licenses of the tools.

## Features

### Tesseract OSD Rotation Detection
- **Automatic rotation detection** using Tesseract OCR's Orientation and Script Detection (OSD)
- **Configurable confidence threshold** for reliable results (default: 0.7)
- **Graceful fallback** to 0° rotation when Tesseract is not available
- **Support for standard angles**: 0°, 90°, 180°, and 270° detection
- **Comprehensive error handling** with detailed logging

**Requirements**: Tesseract OCR (version 4.0+) and `pytesseract` package for automatic detection.

### Using Nemotron-parse

Copy the `.env.example` file change `NEMOTRON_ENDPOINT` to the endpoint of the Nemotron-parse model you want to use.

### Examples
The `example_*.py` scripts contain basic scripts for processing PDF documents using different OCR tools under the hood.

## Migration Guide (v2.0)

### OCR Backend Change

**Important**: As of version 2.0, the default OCR backend for PPTX processing has changed from **Surya** to **Nemotron**.

#### For Existing Users

If you were using the default Surya OCR backend, you have two options:

1. **Continue with Nemotron (recommended)**:
   ```bash
   pip install .[nemotronparse]
   ```

2. **Explicitly use Surya OCR**:
   ```bash
   # Install Surya dependencies
   pip install .[marker]
   
   # Use Surya explicitly
   banyan-extract presentation.pptx output_dir/ --pptx_ocr_backend surya
   ```

#### Code Migration

**Before (v1.x)**:
```python
from banyan_extract import PptxProcessor

# Default was Surya
processor = PptxProcessor()
```

**After (v2.0)**:
```python
from banyan_extract import PptxProcessor

# Default is now Nemotron
processor = PptxProcessor()  # Uses Nemotron by default

# To use Surya explicitly
processor = PptxProcessor(ocr_backend="surya")
```

#### CLI Migration

**Before (v1.x)**:
```bash
# Default was Surya
banyan-extract presentation.pptx output_dir/
```

**After (v2.0)**:
```bash
# Default is now Nemotron
banyan-extract presentation.pptx output_dir/

# To use Surya explicitly
banyan-extract presentation.pptx output_dir/ --pptx_ocr_backend surya
```

## CLI Usage
Use `banyan-extract` to run the tool from the command line. Example command that reads in a PDF named `example.pdf` and puts all the extracted content in a directory named `banyan_output`:

```bash
banyan-extract --backend nemoparse example.pdf banyan_output/
```

### PPTX Processing with Default Nemotron OCR

```bash
# Process PPTX with default Nemotron OCR backend
banyan-extract presentation.pptx output_dir/

# Process PPTX with Surya OCR backend (explicit)
banyan-extract presentation.pptx output_dir/ --pptx_ocr_backend surya
```
