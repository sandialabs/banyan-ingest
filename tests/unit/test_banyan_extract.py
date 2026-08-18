"""
Unit tests for BanyanExtract class (banyan_extract.py).

These tests verify the main entry point wrapper through its public interface only.
Tests mock the HTTP boundary (processor._get_response) but use real file I/O.

Test Organization:
- Initialization tests: __init__() with various configurations
- Configuration validation tests: validate_settings()
- Backend selection tests: Auto-detection logic for PDF/PPTX
- Processing workflow tests: __call__() end-to-end with real files

TDD Principles Applied:
- Test public interfaces only (no processor internals)
- Mock external HTTP boundary only
- Use real file I/O with tmp_path fixture
- Independent expected values (known-good literals)
"""

import pytest
import os
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from banyan_extract.banyan_extract import (
    BanyanExtract,
    validate_file_exists,
    validate_directory_writable,
    validate_rotation_confidence_threshold
)
from banyan_extract.ocr import ModelVersion
from banyan_extract.converter.exceptions import (
    LibreOfficeNotFoundError,
    ConversionFailedError
)


class TestModuleLevelValidationFunctions:
    """Tests for module-level validation functions."""

    def test_validate_file_exists_with_existing_file(self, tmp_path):
        """Validation passes for existing readable file."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        # Should not raise
        validate_file_exists(str(test_file))

    def test_validate_file_exists_raises_for_missing_file(self):
        """Validation raises FileNotFoundError for non-existent file."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            validate_file_exists("/nonexistent/path/file.pdf")

    def test_validate_directory_writable_creates_missing_directory(self, tmp_path):
        """Validation creates directory if it doesn't exist."""
        new_dir = tmp_path / "new_output_dir"
        assert not new_dir.exists()

        validate_directory_writable(str(new_dir))

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_validate_directory_writable_with_existing_directory(self, tmp_path):
        """Validation passes for existing writable directory."""
        # Should not raise
        validate_directory_writable(str(tmp_path))

    def test_validate_rotation_confidence_threshold_valid_values(self):
        """Validation passes for threshold in [0.0, 1.0] range."""
        # Should not raise for valid values
        validate_rotation_confidence_threshold(0.0)
        validate_rotation_confidence_threshold(0.5)
        validate_rotation_confidence_threshold(0.7)
        validate_rotation_confidence_threshold(1.0)

    def test_validate_rotation_confidence_threshold_invalid_values(self):
        """Validation raises ValueError for threshold outside [0.0, 1.0]."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            validate_rotation_confidence_threshold(-0.1)

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            validate_rotation_confidence_threshold(1.5)


class TestBanyanExtractInitialization:
    """Tests for BanyanExtract initialization."""

    def test_init_with_minimal_config(self):
        """Initialize with only required parameters uses defaults."""
        extractor = BanyanExtract(
            input_file="test.pdf",
            output_dir="output/"
        )

        assert extractor.input_file == "test.pdf"
        assert extractor.output_dir == "output/"
        assert extractor.backend == "auto"
        assert extractor.is_input_dir == False
        assert extractor.save_images == False
        assert extractor.save_tables == False
        assert extractor.overwrite == False

    def test_init_with_custom_backend(self):
        """Initialize with explicit backend selection."""
        extractor = BanyanExtract(
            input_file="test.pdf",
            output_dir="output/",
            backend="nemoparse"
        )

        assert extractor.backend == "nemoparse"

    def test_init_with_all_save_flags(self):
        """Initialize with all save flags enabled."""
        extractor = BanyanExtract(
            input_file="test.pdf",
            output_dir="output/",
            save_images=True,
            save_tables=True,
            save_bbox_data=True,
            save_page_numbers=True
        )

        assert extractor.save_images == True
        assert extractor.save_tables == True
        assert extractor.save_bbox_data == True
        assert extractor.save_page_numbers == True

    def test_init_with_rotation_detection_config(self):
        """Initialize with rotation detection parameters."""
        extractor = BanyanExtract(
            input_file="test.pdf",
            output_dir="output/",
            auto_detect_rotation=True,
            rotation_confidence_threshold=0.85,
            rotation_angle=90
        )

        assert extractor.auto_detect_rotation == True
        assert extractor.rotation_confidence_threshold == 0.85
        assert extractor.rotation_angle == 90

    def test_init_with_directory_processing_config(self):
        """Initialize for directory batch processing."""
        extractor = BanyanExtract(
            input_file="input_dir/",
            output_dir="output/",
            is_input_dir=True,
            preserve_input_structure=True,
            recursion_depth=3
        )

        assert extractor.is_input_dir == True
        assert extractor.preserve_input_structure == True
        assert extractor.recursion_depth == 3

    def test_init_with_model_version_enum(self):
        """Initialize with specific model version."""
        extractor = BanyanExtract(
            input_file="test.pdf",
            output_dir="output/",
            model_version=ModelVersion.LEGACY
        )

        assert extractor.model_version == ModelVersion.LEGACY

    def test_init_merges_kwargs_with_defaults(self):
        """Initialize merges provided kwargs with default configuration."""
        extractor = BanyanExtract(
            input_file="test.pdf",
            output_dir="output/",
            temperature=0.5,
            re_run=True
        )

        # Custom values
        assert extractor.temperature == 0.5
        assert extractor.re_run == True
        # Defaults for unspecified
        assert extractor.sort_by_position == False
        assert extractor.checkpointing == False


class TestBanyanExtractProcessingSingleFile:
    """Tests for single-file processing through __call__() method."""

    def test_process_pdf_with_nemoparse_backend_creates_output(self, tmp_path):
        """Process single PDF file creates markdown output."""
        # Use real test PDF from test data
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        # Mock only the HTTP boundary (_get_response in NemotronOCR)
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            # Mock OCR response with complete bbox data
            mock_response.return_value = [
                {
                    "type": "text",
                    "text": "Extracted text from PDF",
                    "bbox": {"xmin": 10.0, "ymin": 20.0, "xmax": 100.0, "ymax": 50.0}
                }
            ]

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            extractor()

            # Verify output file was created (default output_base is "banyan-extract-output")
            output_md = output_dir / "banyan-extract-output.md"
            assert output_md.exists()
            content = output_md.read_text()
            assert "Extracted text from PDF" in content

    def test_process_pdf_with_save_tables_flag(self, tmp_path):
        """Process PDF with save_tables=True creates table files when tables exist."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            # Mock response with a table element
            mock_response.return_value = [
                {"type": "text", "text": "Document text", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 30}},
                {"type": "table", "text": "| A | B |\n| 1 | 2 |", "bbox": {"xmin": 0, "ymin": 40, "xmax": 100, "ymax": 80}}
            ]

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                save_tables=True
            )

            extractor()

            # Verify markdown output includes table
            output_md = output_dir / "banyan-extract-output.md"
            assert output_md.exists()
            content = output_md.read_text()
            assert "| A | B |" in content or "table" in content.lower()

    def test_process_pdf_with_auto_backend_detection(self, tmp_path):
        """Process PDF with backend='auto' detects nemoparse."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Auto-detected backend", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="auto",
                endpoint="http://test:8000"
            )

            extractor()

            # Verify processing completed (backend auto-selected nemoparse)
            output_md = output_dir / "banyan-extract-output.md"
            assert output_md.exists()

    def test_process_with_custom_output_base(self, tmp_path):
        """Process with custom output_base changes output filename."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Custom output", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                output_base="custom_name"
            )

            extractor()

            # Verify custom output filename
            output_md = output_dir / "custom_name.md"
            assert output_md.exists()

    def test_process_with_missing_endpoint_raises_error(self, tmp_path):
        """Process without endpoint configuration raises ValueError."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        extractor = BanyanExtract(
            input_file=str(test_pdf),
            output_dir=str(output_dir),
            backend="nemoparse",
            config_file="/nonexistent/.env"  # Force config file to be missing
            # No endpoint provided
        )

        with pytest.raises(ValueError, match="Config file"):
            extractor()

    def test_process_with_return_bytes_flag(self, tmp_path):
        """Process with return_bytes=True returns bytes instead of writing files."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Text content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                return_bytes=True
            )

            result = extractor()

            # Should return dict with encoding and markdown bytes
            assert isinstance(result, dict)
            assert "markdown" in result
            assert isinstance(result["markdown"], bytes)
            assert b"Text content" in result["markdown"]


class TestBanyanExtractFileConversion:
    """Tests for convert_file method."""

    def test_convert_file_no_converter(self, tmp_path):
        """convert_file returns original filepath when converter is None."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4")

        extractor = BanyanExtract(
            input_file=str(test_pdf),
            output_dir=str(tmp_path / "output"),
            backend="nemoparse",
            endpoint="http://test:8000",
            enable_conversion=False  # Explicitly disable conversion
        )

        # Set converter to None (as __call__() would do)
        extractor.converter = None

        # convert_file should return original path unchanged
        result = extractor.convert_file(str(test_pdf))
        assert result == str(test_pdf)

    def test_convert_file_pdf_no_conversion_needed(self, tmp_path):
        """convert_file returns original PDF filepath without conversion."""
        test_pdf = tmp_path / "document.pdf"
        test_pdf.write_bytes(b"%PDF-1.4")

        # Create extractor with converter initialized
        with patch('banyan_extract.converter.libreoffice_converter.LibreOfficeConverter') as MockConverter:
            mock_converter_instance = Mock()
            MockConverter.return_value = mock_converter_instance

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(tmp_path / "output"),
                backend="nemoparse",
                endpoint="http://test:8000"
            )
            extractor.converter = mock_converter_instance

            result = extractor.convert_file(str(test_pdf))

            # PDF should not be converted
            assert result == str(test_pdf)
            # convert_to_pdf should not have been called
            mock_converter_instance.convert_to_pdf.assert_not_called()

    def test_convert_file_docx_success(self, tmp_path):
        """convert_file successfully converts DOCX to PDF."""
        test_docx = tmp_path / "document.docx"
        test_docx.write_bytes(b"fake docx content")
        converted_pdf = tmp_path / "document.pdf"

        with patch('banyan_extract.converter.libreoffice_converter.LibreOfficeConverter') as MockConverter:
            mock_converter_instance = Mock()
            mock_converter_instance.convert_to_pdf.return_value = str(converted_pdf)
            MockConverter.return_value = mock_converter_instance

            extractor = BanyanExtract(
                input_file=str(test_docx),
                output_dir=str(tmp_path / "output"),
                backend="nemoparse",
                endpoint="http://test:8000"
            )
            extractor.converter = mock_converter_instance

            result = extractor.convert_file(str(test_docx))

            # Should return converted PDF path
            assert result == str(converted_pdf)
            # Converter should have been called with original docx path
            mock_converter_instance.convert_to_pdf.assert_called_once_with(str(test_docx))

    def test_convert_file_libreoffice_not_found(self, tmp_path, caplog):
        """convert_file handles LibreOfficeNotFoundError gracefully."""
        test_docx = tmp_path / "document.docx"
        test_docx.write_bytes(b"fake docx content")

        with patch('banyan_extract.converter.libreoffice_converter.LibreOfficeConverter') as MockConverter:
            mock_converter_instance = Mock()
            mock_converter_instance.convert_to_pdf.side_effect = LibreOfficeNotFoundError(
                "LibreOffice not installed"
            )
            MockConverter.return_value = mock_converter_instance

            extractor = BanyanExtract(
                input_file=str(test_docx),
                output_dir=str(tmp_path / "output"),
                backend="nemoparse",
                endpoint="http://test:8000"
            )
            extractor.converter = mock_converter_instance

            with caplog.at_level(logging.ERROR):
                result = extractor.convert_file(str(test_docx))

            # Should return original filepath (fallback)
            assert result == str(test_docx)
            # Should log error
            assert "LibreOffice not found" in caplog.text

    def test_convert_file_conversion_failed(self, tmp_path, caplog):
        """convert_file handles ConversionFailedError gracefully."""
        test_docx = tmp_path / "document.docx"
        test_docx.write_bytes(b"fake docx content")

        with patch('banyan_extract.converter.libreoffice_converter.LibreOfficeConverter') as MockConverter:
            mock_converter_instance = Mock()
            mock_converter_instance.convert_to_pdf.side_effect = ConversionFailedError(
                "Conversion failed: timeout"
            )
            MockConverter.return_value = mock_converter_instance

            extractor = BanyanExtract(
                input_file=str(test_docx),
                output_dir=str(tmp_path / "output"),
                backend="nemoparse",
                endpoint="http://test:8000"
            )
            extractor.converter = mock_converter_instance

            with caplog.at_level(logging.ERROR):
                result = extractor.convert_file(str(test_docx))

            # Should return original filepath (fallback)
            assert result == str(test_docx)
            # Should log error with exception message
            assert "Conversion failed" in caplog.text

    def test_convert_file_unexpected_exception(self, tmp_path, caplog):
        """convert_file handles unexpected exceptions gracefully."""
        test_docx = tmp_path / "document.docx"
        test_docx.write_bytes(b"fake docx content")

        with patch('banyan_extract.converter.libreoffice_converter.LibreOfficeConverter') as MockConverter:
            mock_converter_instance = Mock()
            mock_converter_instance.convert_to_pdf.side_effect = RuntimeError(
                "Unexpected error during conversion"
            )
            MockConverter.return_value = mock_converter_instance

            extractor = BanyanExtract(
                input_file=str(test_docx),
                output_dir=str(tmp_path / "output"),
                backend="nemoparse",
                endpoint="http://test:8000"
            )
            extractor.converter = mock_converter_instance

            with caplog.at_level(logging.ERROR):
                result = extractor.convert_file(str(test_docx))

            # Should return original filepath (fallback)
            assert result == str(test_docx)
            # Should log unexpected error
            assert "Unexpected conversion error" in caplog.text
