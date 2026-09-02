# AGENTS.md - Guidelines for Agentic Coding in banyan-extract

This file provides guidance to coding agents when working with code in this repository.

## Repository Overview

**Banyan Extract** is a Python module for preparing documents for GenAI and LLM applications. It provides document processing capabilities with support for multiple OCR backends and file formats.

### Key Features

- **Multi-backend OCR**: Supports Nemotron (default) and Surya OCR backends
- **File format support**: PDF and PPTX processing
- **Rotation detection**: Automatic rotation correction using Tesseract OCR
- **Batch processing**: Process directories of documents recursively
- **Flexible output**: Save markdown, images, bounding boxes, tables, and page numbers

## Style and Conventions

- **No emojis** anywhere in the codebase. If you find one, remove it.
- **File naming**: Use descriptive names (e.g., `chat_service.py`, `mcp_tool_manager.py`), not generic ones (`utils.py`, `helpers.py`). Exception: top-level entry points.
- **File size**: Prefer 400 lines or fewer.
- **Documentation**: PRs must update relevant docs in `/docs` (architecture, features, API, config, troubleshooting).
- **Changelog**: Add a 1-2 line entry to `CHANGELOG.md` for every PR. Format: `### PR #<number> - YYYY-MM-DD`.
- **Date stamps**: Include `YYYY-MM-DD` dates in doc filenames or section headers to track staleness.

## Development Commands

### Installation

```bash
pip install .                      # Install from source
pip install .[nemotronparse]       # With Nemotron OCR support (default for PPTX)
pip install .[marker]              # With Surya OCR support
pip install .[autorotate]          # With rotation detection support
pip install -e .                   # Install in development mode
```

### Testing

```bash
python3 -m pytest tests/                                    # Run all tests
python3 -m pytest tests/unit/                               # Unit tests only
python3 -m pytest tests/integration/                        # Integration tests only
python3 -m pytest tests/unit/test_nemoparse_processor.py    # Specific test file
python3 -m pytest tests/unit/test_nemoparse_processor.py::test_nemoparse_processor_initialization  # Specific test
python3 -m pytest -v tests/                                 # Verbose output
python3 -m pytest -s tests/                                 # See print output
python3 -m pytest -x tests/                                 # Stop on first failure
python3 -m pytest --cov=src/banyan_extract tests/           # With coverage
python3 -m pytest -m unit tests/                            # Only unit-marked tests
python3 -m pytest -m integration tests/                     # Only integration-marked tests
python3 -m pytest -m "not slow" tests/                      # Skip slow tests
```

### Linting and Formatting

```bash
python3 -m ruff check src/        # Run ruff linter
python3 -m ruff format src/       # Run ruff formatter
python3 -m flake8 src/            # Run flake8
```

### Building

```bash
python -m build                   # Build the package
./build_pypi.sh                   # Build for PyPI distribution
```

### Running

```bash
banyan-extract input.pdf output_dir/                              # Single PDF
banyan-extract presentation.pptx output_dir/                      # PPTX with default Nemotron OCR
banyan-extract input_dir/ output_dir/ --is_input_dir              # Directory recursively
banyan-extract input.pdf output_dir/ --auto_detect_rotation       # With rotation detection
banyan-extract input.pdf output_dir/ --backend nemoparse          # Specific backend
```

## Code Architecture

### High-Level Structure

```
src/banyan_extract/
├── cli.py                          # CLI entry point and argument parsing
├── banyan_extract.py               # Main wrapper class (BanyanExtract)
├── processor/                      # Document processors (strategy pattern)
│   ├── processor.py                # Abstract base class
│   ├── nemoparse_processor.py      # Nemotron Parse processor
│   ├── marker_processor.py         # Marker PDF processor
│   ├── pptx_processor.py          # PPTX processor
│   └── papermage_processor.py      # PaperMage processor
├── output/                         # Output handlers
│   ├── output.py                   # Abstract base class
│   ├── nemoparse_output.py         # Nemoparse output handler
│   ├── marker_output.py            # Marker output handler
│   ├── pptx_output.py             # PPTX output handler
│   └── papermage_output.py         # PaperMage output handler
├── converter/                      # File conversion utilities
│   ├── pdf_to_image.py             # PDF to image conversion
│   └── latex_table_to_csv.py       # LaTeX table conversion
├── ocr/                            # OCR modules
│   └── nemotron_ocr.py             # Nemotron OCR wrapper
└── utils/                          # Utility functions
    ├── image_rotation.py           # Image rotation utilities
    ├── rotation_detection.py       # Tesseract-based rotation detection
    ├── dependencies.py             # Dependency checking
    ├── file_gather.py              # File discovery utilities
    └── logging_config.py           # Logging configuration
```

### Key Design Patterns

1. **Processor Pattern**: All processors inherit from the abstract `Processor` base class
   - Common interface: `process_document()` and `process_batch_documents()`
   - Each processor handles a specific document type/backend

2. **Output Handler Pattern**: Each processor has a corresponding output class
   - Inherits from `ModelOutput` base class
   - Handles saving extracted content in various formats

3. **Strategy Pattern**: Different OCR backends can be selected
   - PPTX processor supports both Nemotron and Surya OCR
   - Backend selection via configuration

4. **Factory Pattern**: CLI acts as a factory
   - Creates appropriate processor instances based on file type and arguments
   - Auto-detects backend when not explicitly specified

### Data Flow

1. **CLI Entry**: User runs `banyan-extract` command with arguments
2. **Processor Selection**: CLI determines appropriate processor based on file extension, backend argument, or auto-detection
3. **Document Processing**: Selected processor converts to images (if needed), applies rotation correction (if enabled), performs OCR, extracts text/tables/content
4. **Output Generation**: Processor creates output objects containing extracted text, images, bounding boxes, tables, and page numbers
5. **Output Saving**: Output objects save results as markdown, images, bounding box data, tables as CSV

### Backend Support Matrix

| Processor | OCR Backend | Rotation Detection | Batch Processing |
|-----------|-------------|--------------------|------------------|
| NemoparseProcessor | Nemotron | Yes | Yes |
| MarkerProcessor | Surya | No | Yes |
| PptxProcessor | Nemotron (default) | No | Yes |
| PptxProcessor | Surya | No | Yes |
| PaperMageProcessor | PaperMage | No | Yes |

## Code Style Guidelines

### Imports

Group imports in this order: standard library, third-party, local application. Use absolute imports for local modules. Avoid wildcard imports (except in `__init__.py`).

```python
from banyan_extract.processor import Processor
```

### Formatting

- **Line length**: Maximum 120 characters
- **Indentation**: 4 spaces (no tabs)
- **Spacing**: Two blank lines around top-level functions/classes, one blank line around methods
- **Quotes**: Double quotes for strings unless single quotes are needed
- **Docstrings**: Google-style for public functions and classes

### Type Hints

- Use type hints for all function parameters and return values
- Use PEP 604 union syntax (`X | Y`) instead of `Union[X, Y]`
- Use `Optional[X]` for nullable types

### Naming Conventions

- **Variables and functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: Leading underscore (`_encode_image`)
- **Booleans**: Prefix with `is_`, `has_`, or `can_`

### Error Handling

Use specific exceptions instead of generic `Exception`. Provide meaningful error messages. Clean up resources in `finally` blocks when needed.

### Documentation

Use Google-style docstrings:

```python
def sort_elements_by_position(self, bbox_data, width, height):
    """
    Sort document elements based on their spatial position.

    Args:
        bbox_data: List of element dictionaries from API response
        width: Page width in pixels
        height: Page height in pixels

    Returns:
        List of sorted element dictionaries
    """
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```ini
NEMOPARSE_ENDPOINT="https://your-nemotron-endpoint.com"
NEMOPARSE_MODEL="nvidia/nemoretriever-parse"
PPTX_NEMOTRON_ENDPOINT="https://your-pptx-endpoint.com"    # Optional
PPTX_NEMOTRON_MODEL="nvidia/nemotron-parse"                 # Optional
```

### Default Configuration Values

The `BanyanExtract` class has these defaults (in `banyan_extract.py`):

- `backend`: "auto" (auto-detects based on file extension)
- `pptx_ocr_backend`: "nemotron" (default for PPTX files)
- `auto_detect_rotation`: False
- `rotation_confidence_threshold`: 0.7
- `sort_by_position`: True
- `overwrite`: False
- `save_images`: False
- `save_bbox_data`: False
- `save_tables`: False
- `save_page_numbers`: False
- `return_bytes`: False

## Testing Strategy

### Test Organization

- **Unit tests**: `tests/unit/` - Test individual components in isolation
- **Integration tests**: `tests/integration/` - Test complete workflows
- **Test utilities**: `tests/utils.py` - Shared test fixtures and utilities

### Test Markers

- `@pytest.mark.unit`: Unit test
- `@pytest.mark.integration`: Integration test
- `@pytest.mark.slow`: Slow test
- `@pytest.mark.external`: Requires external services
- `@pytest.mark.meta`: Tests about tests

### Test Guidelines

- Write unit tests for all new functionality
- Use pytest as the test runner
- Mock external dependencies in unit tests
- Test both success and failure cases

## Common Development Tasks

### Adding a New Processor

1. Create a new processor class in `src/banyan_extract/processor/` inheriting from `Processor`
2. Implement `process_document()` and `process_batch_documents()`
3. Create corresponding output handler in `src/banyan_extract/output/`
4. Update CLI to recognize and instantiate the new processor
5. Add tests in `tests/unit/` and `tests/integration/`

### Adding a New Feature

1. Identify which processor(s) need the feature
2. Add implementation to processor class
3. Update output handler if needed
4. Add feature flag to CLI argument parser
5. Add feature to `BanyanExtract` wrapper class
6. Write unit and integration tests

### Debugging

```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python -m banyan_extract input.pdf output/ --backend nemoparse 2>&1 | tee debug.log

# Check dependency status
from banyan_extract.utils.dependencies import log_dependency_status
log_dependency_status()
```

## Dependencies

### Required

- python-pptx, pandas, pdf2image, python-dotenv

### Optional (installed via extras)

- `nemotronparse`: openai (Nemotron OCR support)
- `marker`: marker-pdf, surya-ocr (Surya OCR support)
- `autorotate`: Tesseract rotation detection

Check dependencies at runtime:
```python
from banyan_extract.utils.dependencies import has_marker_dependencies, has_nemotronparse_dependencies
```

## Important Notes

- **Nemotron is the default OCR backend** for PPTX processing (changed from Surya in v2.0)
- **Rotation detection only works** with NemoparseProcessor (not Marker, PPTX, or PaperMage)
- **re_run and temperature flags** only work with NemoparseProcessor
- **Python requirement**: 3.10+

## Version Control and CI

- Use feature branches for new development
- Write meaningful commit messages; keep commits small and focused
- Run tests before committing
- Update documentation when making changes
- All tests must pass before pushing (GitHub Actions CI/CD)

## Documentation

Key documentation files:

- `README.md`: Installation and basic usage
- `docs/USAGE_GUIDE.md`: Comprehensive usage guide with examples
- `docs/codebase.md`: Codebase structure and architecture
- `docs/processor_api.md`: Processor API documentation
- `docs/rotation_api.md`: Rotation detection API
- `docs/troubleshooting.md`: Troubleshooting guide
