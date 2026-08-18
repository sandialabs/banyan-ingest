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

#### Rottaion Detection
For the **rotation detection** functionality, you need Tesseract OCR (version 4.0 or higher recommended) installed on your system

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

### Using Nemotron-parse
Copy the `.env.example` file change `NEMOTRON_ENDPOINT` to the endpoint of the Nemotron-parse model you want to use.

## Features

### Column-Aware Sorting for Multi-Column Documents
- **Automatic column detection** using gap-based analysis for multi-column layouts (scientific papers, newspapers, magazines)
- **Smart reading order** - reads each column top-to-bottom before moving to the next column
- **Handles ragged edges** - tolerates x-coordinate variation within columns from OCR noise
- **Configurable sensitivity** via `column_gap_threshold` parameter (default: 0.15)
- **Graceful fallback** - automatically detects single-column documents
- **Special footer handling** - page footers appear after all columns (not mid-column)

**Key Benefits**:
- Fixes interleaved text from multi-column PDFs
- Works with 2, 3, or more columns
- No manual column configuration needed
- Can be disabled for single-column documents

See [Column Detection Documentation](#column-detection-for-multi-column-documents) for usage examples.

### Tesseract OSD Rotation Detection
- **Automatic rotation detection** using Tesseract OCR's Orientation and Script Detection (OSD)
- **Configurable confidence threshold** for reliable results (default: 0.7)
- **Graceful fallback** to 0° rotation when Tesseract is not available
- **Support for standard angles**: 0°, 90°, 180°, and 270° detection
- **Comprehensive error handling** with detailed logging

**Requirements**: Tesseract OCR (version 4.0+) and `pytesseract` package for automatic detection.

### Examples
The `example_*.py` scripts contain basic scripts for processing PDF documents using different OCR tools under the hood.

## CLI Usage
Use `banyan-extract` to run the tool from the command line. Example command that reads in a PDF named `example.pdf` and puts all the extracted content in a directory named `banyan_output`:

```bash
banyan-extract --backend nemoparse example.pdf banyan_output/
```

### Directory Processing (Recursive)
Process all supported files in a directory and its subdirectories:
```bash
banyan-extract input_dir/ output_dir/ --is_input_dir
```

### Custom File Extensions
Filter files by specific extensions:
```bash
banyan-extract input_dir/ output_dir/ --is_input_dir --file_extensions "pdf,pptx"
```

### PPTX Processing with Default Nemotron OCR

```bash
# Process PPTX with default Nemotron OCR backend
banyan-extract presentation.pptx output_dir/

# Process PPTX with Surya OCR backend (explicit)
banyan-extract presentation.pptx output_dir/ --pptx_ocr_backend surya
```

### Column Detection for Multi-Column Documents

The column detection feature automatically detects and handles multi-column layouts (e.g., scientific papers, newspapers) for correct reading order.

**Default behavior (column detection enabled):**
```bash
# Automatically detects and handles multi-column layouts
banyan-extract paper.pdf output/ --sort_by_position
```

**Disable column detection** for single-column documents or if detection causes issues:
```bash
banyan-extract paper.pdf output/ --column_detection_mode none
```

**Adjust detection sensitivity:**
```bash
# More sensitive (detects columns with smaller gaps)
banyan-extract paper.pdf output/ --column_gap_threshold 0.10

# Less sensitive (requires larger gaps between columns)
banyan-extract paper.pdf output/ --column_gap_threshold 0.25
```

**How it works:**
- Detects columns by finding gaps in x-coordinates (default threshold: 15% of page width)
- Sorts elements within each column by y-position (top to bottom)
- Reads left column completely, then right column (left-to-right order)
- Handles ragged column edges from OCR variation
- Page footers always appear after all columns

**When to use:**
- Scientific papers (typically 1-2 columns)
- Newspapers (3+ columns)
- Magazine layouts
- Conference proceedings
- Disable for pure single-column documents (slight performance gain)

### Saving output

Use `--save_images`, `--save_bbox_data`, and `--save_tables`  if you would like to save all detected images, bbox data (includes text), and tables as csv. 

By default `banyan-extract` cli will save the reconstructed markdown

## Standalone usage
We are defining standalone usage as using Banyan Extract directly and not as a service/part of a larger framework or workflow.

It is recommended you use the cli or `BanyanExtract` wrapper class for standalone usage.

## Usage as a server
We recommend you work with processors directly so you can do custom preprocessing as well as data post-processing
