"""
Unit tests for CLI module (cli.py).

These tests verify the command-line interface functionality including
argument parsing and main() function execution.

Test Organization:
- Argument parsing tests: Test parse_arguments() function comprehensively
- Main function tests: Test main() execution and integration
"""

import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path

from banyan_extract.cli import parse_arguments, main, validate_rotation_confidence_threshold
from banyan_extract.ocr import ModelVersion


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_parse_required_arguments(self):
        """Test that required arguments input_file and output_dir are parsed."""
        test_args = ["input.pdf", "output/"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            args = parse_arguments()
            assert args.input_file == "input.pdf"
            assert args.output_dir == "output/"
            assert args.backend == "auto"  # Default

    def test_parse_with_all_boolean_flags(self):
        """Test that all boolean flags are parsed correctly."""
        test_args = [
            "input.pdf", "output/",
            "--is_input_dir",
            "--preserve_input_structure",
            "--checkpointing",
            "--draw_bboxes",
            "--save_bbox_data",
            "--save_images",
            "--save_tables",
            "--save_page_numbers",
            "--return_bytes",
            "--sort_by_position",
            "--overwrite",
            "--re_run",
            "--auto_detect_rotation",
            "--apply_contrast_filter",
            "--enable_conversion"
        ]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            args = parse_arguments()
            assert args.is_input_dir == True
            assert args.preserve_input_structure == True
            assert args.checkpointing == True
            assert args.draw_bboxes == True
            assert args.save_bbox_data == True
            assert args.save_images == True
            assert args.save_tables == True
            assert args.save_page_numbers == True
            assert args.return_bytes == True
            assert args.sort_by_position == True
            assert args.overwrite == True
            assert args.re_run == True
            assert args.auto_detect_rotation == True
            assert args.apply_contrast_filter == True
            assert args.enable_conversion == True

    def test_parse_backend_selection(self):
        """Test --backend argument with different values."""
        backends = ["auto", "nemoparse", "marker", "pptx"]
        for backend in backends:
            test_args = ["input.pdf", "output/", "--backend", backend]
            with patch('sys.argv', ['banyan-extract'] + test_args):
                args = parse_arguments()
                assert args.backend == backend

    def test_parse_rotation_arguments(self):
        """Test rotation-related arguments."""
        test_args = [
            "input.pdf", "output/",
            "--rotation_angle", "90",
            "--auto_detect_rotation",
            "--rotation_confidence_threshold", "0.85"
        ]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.cli.logger'):  # Mock logger to suppress warning
                args = parse_arguments()
                assert args.rotation_angle == 90.0
                assert args.auto_detect_rotation == True
                assert args.rotation_confidence_threshold == 0.85

    def test_parse_save_flags(self):
        """Test all save-related flags."""
        test_args = [
            "input.pdf", "output/",
            "--save_images",
            "--save_tables",
            "--save_bbox_data",
            "--save_page_numbers"
        ]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            args = parse_arguments()
            assert args.save_images == True
            assert args.save_tables == True
            assert args.save_bbox_data == True
            assert args.save_page_numbers == True

    def test_parse_pptx_arguments(self):
        """Test PPTX-specific arguments."""
        test_args = [
            "input.pptx", "output/",
            "--pptx_ocr_backend", "nemotron",
            "--pptx_nemotron_endpoint", "http://test:8000",
            "--pptx_nemotron_model", "test-model"
        ]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            args = parse_arguments()
            assert args.pptx_ocr_backend == "nemotron"
            assert args.pptx_nemotron_endpoint == "http://test:8000"
            assert args.pptx_nemotron_model == "test-model"

    def test_parse_conversion_arguments(self):
        """Test LibreOffice conversion arguments."""
        test_args = [
            "input.docx", "output/",
            "--enable_conversion",
            "--libreoffice_path", "/usr/bin/libreoffice",
            "--conversion_temp_dir", "/tmp/conversions"
        ]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            args = parse_arguments()
            assert args.enable_conversion == True
            assert args.libreoffice_path == "/usr/bin/libreoffice"
            assert args.conversion_temp_dir == "/tmp/conversions"

    def test_parse_recursion_depth(self):
        """Test --recursion_depth with valid values."""
        test_cases = [
            ("0", 0),    # Only root directory
            ("1", 1),    # Default - root + immediate subdirectories
            ("5", 5),    # Specific depth
            ("-1", -1)   # Infinite recursion
        ]
        for depth_str, expected_depth in test_cases:
            test_args = ["input/", "output/", "--recursion_depth", depth_str]
            with patch('sys.argv', ['banyan-extract'] + test_args):
                args = parse_arguments()
                assert args.recursion_depth == expected_depth

    def test_parse_file_extensions(self):
        """Test --file_extensions comma-separated list."""
        test_args = ["input/", "output/", "--file_extensions", "pdf,pptx,docx"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            args = parse_arguments()
            assert args.effective_extensions == {"pdf", "pptx", "docx"}

    def test_parse_model_version(self):
        """Test --model_version enum parsing."""
        test_args = ["input.pdf", "output/", "--model_version", "latest"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            args = parse_arguments()
            assert args.model_version == ModelVersion.LATEST

        test_args = ["input.pdf", "output/", "--model_version", "legacy"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            args = parse_arguments()
            assert args.model_version == ModelVersion.LEGACY

    def test_invalid_rotation_confidence_raises_error(self):
        """Test that rotation_confidence_threshold outside [0.0, 1.0] exits."""
        test_args = ["input.pdf", "output/", "--rotation_confidence_threshold", "1.5"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            with pytest.raises(SystemExit):  # argparse calls sys.exit on error
                parse_arguments()

        test_args = ["input.pdf", "output/", "--rotation_confidence_threshold", "-0.1"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_invalid_pptx_backend_raises_error(self):
        """Test that invalid PPTX OCR backend exits."""
        test_args = ["input.pptx", "output/", "--pptx_ocr_backend", "invalid"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_invalid_file_extensions_raises_error(self):
        """Test that empty or malformed file_extensions exits."""
        # Empty extension in list
        test_args = ["input/", "output/", "--file_extensions", "pdf,,pptx"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_re_run_with_non_nemoparse_raises_error(self):
        """Test early validation: re_run with non-nemoparse backend exits."""
        test_args = ["input.pdf", "output/", "--backend", "marker", "--re_run"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_temperature_with_non_nemoparse_raises_error(self):
        """Test early validation: temperature with non-nemoparse backend exits."""
        test_args = ["input.pdf", "output/", "--backend", "pptx", "--temperature", "0.5"]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_rotation_angle_and_auto_detect_warning(self):
        """Test that both manual rotation and auto detection logs a warning."""
        test_args = [
            "input.pdf", "output/",
            "--rotation_angle", "90",
            "--auto_detect_rotation"
        ]
        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.cli.logger') as mock_logger:
                args = parse_arguments()
                # Verify warning was logged
                mock_logger.warning.assert_any_call(
                    'Both manual rotation angle and auto rotation detection are specified. '
                    'Manual rotation will take precedence over auto detection.'
                )


class TestCLIMainFunction:
    """Tests for main() function execution and integration."""

    def test_main_creates_extractor_with_parsed_args(self, tmp_path):
        """Test that main() creates BanyanExtract with all parsed arguments."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF")

        test_args = [
            str(test_pdf),
            str(tmp_path / "output"),
            "--backend", "nemoparse",
            "--endpoint", "http://test:8000",
            "--model_name", "test-model",
            "--save_images"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.cli.BanyanExtract') as mock_extractor_class:
                mock_instance = Mock()
                mock_extractor_class.return_value = mock_instance

                main()

                # Verify BanyanExtract was created with all args
                mock_extractor_class.assert_called_once()
                call_kwargs = mock_extractor_class.call_args[1]
                assert call_kwargs['backend'] == 'nemoparse'
                assert call_kwargs['endpoint'] == 'http://test:8000'
                assert call_kwargs['model_name'] == 'test-model'
                assert call_kwargs['save_images'] == True

                # Verify extractor was called
                mock_instance.assert_called_once()

    def test_main_calls_extractor_with_args(self, tmp_path):
        """Test that main() calls extractor() with correct parameters."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF")

        test_args = [
            str(test_pdf),
            str(tmp_path / "output"),
            "--output_base", "custom_base"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.cli.BanyanExtract') as mock_extractor_class:
                mock_instance = Mock()
                mock_extractor_class.return_value = mock_instance

                main()

                # Verify extractor called with specific params
                mock_instance.assert_called_once()
                call_kwargs = mock_instance.call_args[1]
                assert call_kwargs['input_file'] == str(test_pdf)
                assert call_kwargs['output_dir'] == str(tmp_path / "output")
                assert call_kwargs['output_base'] == 'custom_base'

    def test_main_with_minimal_arguments(self, tmp_path):
        """Test main() with only required arguments."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF")

        test_args = [str(test_pdf), str(tmp_path / "output")]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.cli.BanyanExtract') as mock_extractor_class:
                mock_instance = Mock()
                mock_extractor_class.return_value = mock_instance

                main()

                # Should succeed with defaults
                mock_extractor_class.assert_called_once()
                mock_instance.assert_called_once()

    def test_main_with_all_arguments(self, tmp_path):
        """Test main() with all flags to verify complete propagation."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF")

        test_args = [
            str(test_pdf),
            str(tmp_path / "output"),
            "--backend", "nemoparse",
            "--endpoint", "http://test:8000",
            "--model_name", "test-model",
            "--output_base", "test",
            "--save_images",
            "--save_tables",
            "--save_bbox_data",
            "--overwrite",
            "--temperature", "0.5",
            "--re_run"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.cli.BanyanExtract') as mock_extractor_class:
                mock_instance = Mock()
                mock_extractor_class.return_value = mock_instance

                main()

                call_kwargs = mock_extractor_class.call_args[1]
                assert call_kwargs['save_images'] == True
                assert call_kwargs['save_tables'] == True
                assert call_kwargs['save_bbox_data'] == True
                assert call_kwargs['overwrite'] == True
                assert call_kwargs['temperature'] == 0.5
                assert call_kwargs['re_run'] == True

    def test_main_handles_file_not_found(self, tmp_path):
        """Test main() with non-existent file."""
        test_args = ["/nonexistent/file.pdf", str(tmp_path / "output")]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.cli.BanyanExtract') as mock_extractor_class:
                mock_instance = Mock()
                mock_extractor_class.return_value = mock_instance
                # Simulate validation error
                mock_instance.side_effect = FileNotFoundError("File not found")

                with pytest.raises(FileNotFoundError):
                    main()

    def test_main_handles_missing_endpoint(self, tmp_path):
        """Test main() with missing endpoint configuration."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF")

        test_args = [str(test_pdf), str(tmp_path / "output"), "--backend", "nemoparse"]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.cli.BanyanExtract') as mock_extractor_class:
                mock_instance = Mock()
                mock_extractor_class.return_value = mock_instance
                # Simulate missing endpoint error
                mock_instance.side_effect = ValueError("not found or empty")

                with pytest.raises(ValueError, match="not found or empty"):
                    main()

    def test_main_handles_missing_dependencies(self, tmp_path):
        """Test main() handles ImportError gracefully."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF")

        test_args = [str(test_pdf), str(tmp_path / "output"), "--backend", "marker"]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.cli.BanyanExtract') as mock_extractor_class:
                mock_instance = Mock()
                mock_extractor_class.return_value = mock_instance
                # Simulate missing dependencies
                mock_instance.side_effect = ImportError("MarkerProcessor not available")

                with pytest.raises(ImportError, match="not available"):
                    main()

    def test_main_with_auto_detect_rotation_checks_tesseract(self, tmp_path):
        """Test main() checks Tesseract dependencies when auto-detection enabled."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF")

        test_args = [
            str(test_pdf),
            str(tmp_path / "output"),
            "--auto_detect_rotation"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            # Mock dependency check to simulate missing Tesseract
            with patch('banyan_extract.cli.logger') as mock_logger:
                # Simulate has_tesseract_dependencies returning False
                import_path = 'banyan_extract.utils.tesseract_dependencies.has_tesseract_dependencies'
                with patch(import_path, return_value=False):
                    with patch('banyan_extract.cli.BanyanExtract') as mock_extractor_class:
                        mock_instance = Mock()
                        mock_extractor_class.return_value = mock_instance

                        main()

                        # Verify warning was logged about missing Tesseract
                        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                        assert any("Tesseract" in call for call in warning_calls)


class TestCLIValidationFunctions:
    """Tests for CLI validation helper functions."""

    def test_validate_rotation_confidence_threshold_valid(self):
        """Test validation passes for valid threshold values."""
        # Should not raise
        validate_rotation_confidence_threshold(0.0)
        validate_rotation_confidence_threshold(0.5)
        validate_rotation_confidence_threshold(0.7)
        validate_rotation_confidence_threshold(1.0)

    def test_validate_rotation_confidence_threshold_invalid(self):
        """Test validation raises ValueError for invalid threshold."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            validate_rotation_confidence_threshold(-0.1)

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            validate_rotation_confidence_threshold(1.5)

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            validate_rotation_confidence_threshold(2.0)


class TestCLIEndToEndIntegration:
    """End-to-end integration tests for CLI with real file I/O."""

    def test_cli_processes_real_pdf_creates_markdown(self, tmp_path):
        """CLI processes real PDF and creates markdown output file."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        test_args = [
            str(test_pdf),
            str(output_dir),
            "--backend", "nemoparse",
            "--endpoint", "http://test:8000"
        ]

        # Mock only HTTP boundary
        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
                mock_response.return_value = [
                    {"type": "text", "text": "CLI extracted text", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
                ]

                main()

                # Verify markdown file was created
                output_md = output_dir / "banyan-extract-output.md"
                assert output_md.exists()
                content = output_md.read_text()
                assert "CLI extracted text" in content

    def test_cli_with_custom_output_base_creates_named_file(self, tmp_path):
        """CLI with --output_base creates file with custom name."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        test_args = [
            str(test_pdf),
            str(output_dir),
            "--backend", "nemoparse",
            "--endpoint", "http://test:8000",
            "--output_base", "my_custom_output"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
                mock_response.return_value = [
                    {"type": "text", "text": "Custom output", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
                ]

                main()

                # Verify custom-named file was created
                output_md = output_dir / "my_custom_output.md"
                assert output_md.exists()
                assert "Custom output" in output_md.read_text()

    def test_cli_with_save_bbox_data_flag(self, tmp_path):
        """CLI with --save_bbox_data creates bbox JSON file."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        test_args = [
            str(test_pdf),
            str(output_dir),
            "--backend", "nemoparse",
            "--endpoint", "http://test:8000",
            "--save_bbox_data"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
                mock_response.return_value = [
                    {"type": "text", "text": "Text with bbox", "bbox": {"xmin": 10, "ymin": 20, "xmax": 100, "ymax": 50}}
                ]

                main()

                # Verify bbox data file was created
                bbox_file = output_dir / "banyan-extract-output_bbox.json"
                assert bbox_file.exists()

                import json
                bbox_data = json.loads(bbox_file.read_text())
                assert isinstance(bbox_data, list)

    def test_cli_with_overwrite_flag_replaces_existing_file(self, tmp_path):
        """CLI with --overwrite replaces existing output files."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing output file
        existing_output = output_dir / "banyan-extract-output.md"
        existing_output.write_text("Old content")
        original_mtime = existing_output.stat().st_mtime

        test_args = [
            str(test_pdf),
            str(output_dir),
            "--backend", "nemoparse",
            "--endpoint", "http://test:8000",
            "--overwrite"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
                mock_response.return_value = [
                    {"type": "text", "text": "New content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
                ]

                import time
                time.sleep(0.01)  # Ensure different mtime
                main()

                # Verify file was overwritten
                assert existing_output.exists()
                content = existing_output.read_text()
                assert "New content" in content
                assert "Old content" not in content

    def test_cli_with_auto_backend_for_pdf(self, tmp_path):
        """CLI with backend='auto' correctly selects nemoparse for PDF."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        test_args = [
            str(test_pdf),
            str(output_dir),
            "--backend", "auto",
            "--endpoint", "http://test:8000"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
                mock_response.return_value = [
                    {"type": "text", "text": "Auto-detected PDF processing", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
                ]

                main()

                # Verify processing completed successfully
                output_md = output_dir / "banyan-extract-output.md"
                assert output_md.exists()
                assert "Auto-detected PDF processing" in output_md.read_text()

    def test_cli_creates_output_directory_if_missing(self, tmp_path):
        """CLI creates output directory if it doesn't exist."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "new_output_dir"
        assert not output_dir.exists()

        test_args = [
            str(test_pdf),
            str(output_dir),
            "--backend", "nemoparse",
            "--endpoint", "http://test:8000"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
                mock_response.return_value = [
                    {"type": "text", "text": "Output", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
                ]

                main()

                # Verify directory was created
                assert output_dir.exists()
                assert output_dir.is_dir()
                assert (output_dir / "banyan-extract-output.md").exists()

    def test_cli_with_temperature_parameter(self, tmp_path):
        """CLI passes temperature parameter through to processor."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        test_args = [
            str(test_pdf),
            str(output_dir),
            "--backend", "nemoparse",
            "--endpoint", "http://test:8000",
            "--temperature", "0.7"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
                mock_response.return_value = [
                    {"type": "text", "text": "Temperature test", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
                ]

                main()

                # Verify temperature was passed to OCR
                assert mock_response.called
                call_kwargs = mock_response.call_args[1]
                assert call_kwargs['temperature'] == 0.7

    def test_cli_with_rotation_angle(self, tmp_path):
        """CLI with --rotation_angle processes rotated documents."""
        test_pdf = Path("tests/data/docs/sample.pdf")
        output_dir = tmp_path / "output"

        test_args = [
            str(test_pdf),
            str(output_dir),
            "--backend", "nemoparse",
            "--endpoint", "http://test:8000",
            "--rotation_angle", "90"
        ]

        with patch('sys.argv', ['banyan-extract'] + test_args):
            with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
                mock_response.return_value = [
                    {"type": "text", "text": "Rotated content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
                ]

                main()

                # Verify output was created
                output_md = output_dir / "banyan-extract-output.md"
                assert output_md.exists()
                assert "Rotated content" in output_md.read_text()
