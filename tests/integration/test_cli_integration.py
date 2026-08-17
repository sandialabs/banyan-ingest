"""
Integration tests for CLI end-to-end workflows.

Tests the banyan-extract CLI command-line interface:
- Single file processing via CLI
- Directory batch processing
- CLI argument combinations (backend, save options, rotation)
- Error handling for invalid arguments
- Exit codes

These tests call the CLI main() function directly with sys.argv manipulation,
which allows mocking to work (subprocess would run in separate process).
"""

import pytest
import sys
import shutil
from pathlib import Path
from unittest.mock import patch
from banyan_extract.cli import main as cli_main


class TestCLIIntegration:
    """Integration tests for CLI end-to-end workflows."""

    @pytest.fixture
    def cli_batch_dir(self, tmp_path, test_data_dir):
        """Create directory with test documents for CLI batch tests."""
        batch_dir = tmp_path / "cli_batch"
        batch_dir.mkdir()

        # Copy test files
        source_pdf = test_data_dir / "docs" / "sample.pdf"
        source_pptx = test_data_dir / "docs" / "slides.pptx"

        # Create 3 PDFs and 2 PPTX files
        for i in range(3):
            shutil.copy(source_pdf, batch_dir / f"doc_{i}.pdf")
        for i in range(2):
            shutil.copy(source_pptx, batch_dir / f"slides_{i}.pptx")

        return batch_dir

    @pytest.fixture
    def nested_cli_dir(self, tmp_path, test_data_dir):
        """Create nested directory structure for CLI recursion tests."""
        root = tmp_path / "nested"
        root.mkdir()

        source_pdf = test_data_dir / "docs" / "sample.pdf"

        # Root level: 2 files
        for i in range(2):
            shutil.copy(source_pdf, root / f"root_{i}.pdf")

        # Subdirectory: 2 files
        subdir = root / "subdir"
        subdir.mkdir()
        for i in range(2):
            shutil.copy(source_pdf, subdir / f"sub_{i}.pdf")

        return root

    def test_cli_single_file_processing(self, tmp_path, test_data_dir):
        """CLI: Process single file end-to-end."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock HTTP boundary
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "CLI test content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            # Call CLI main() with sys.argv
            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                           "--backend", "nemoparse", "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        # Verify output file created
        output_file = output_dir / "banyan-extract-output.md"
        assert output_file.exists(), "Expected markdown output file"
        content = output_file.read_text()
        assert "CLI test content" in content

    def test_cli_directory_processing(self, cli_batch_dir, tmp_path):
        """CLI: Process directory with --is_input_dir flag."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Directory content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(cli_batch_dir), str(output_dir),
                           "--is_input_dir", "--backend", "nemoparse",
                           "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        # Verify multiple output files (3 PDFs + 2 PPTX = 5 files)
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 5, f"Expected 5 output files, got {len(output_files)}"

    def test_cli_with_auto_detect_rotation(self, tmp_path, test_data_dir):
        """CLI: Process with --auto_detect_rotation flag."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Rotated content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            # Mock rotation detection
            with patch('banyan_extract.utils.rotation_detection.detect_rotation_angle') as mock_detect:
                mock_detect.return_value = (90, 0.95)  # 90 degrees, high confidence

                original_argv = sys.argv
                try:
                    sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                               "--auto_detect_rotation", "--backend", "nemoparse",
                               "--endpoint", "http://test:8000", "--model_name", "test-model"]
                    cli_main()
                finally:
                    sys.argv = original_argv

        assert (output_dir / "banyan-extract-output.md").exists()

    def test_cli_with_backend_selection(self, tmp_path, test_data_dir):
        """CLI: Specify backend explicitly via --backend flag."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Backend test", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                           "--backend", "nemoparse",
                           "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        assert (output_dir / "banyan-extract-output.md").exists()

    def test_cli_with_save_images_flag(self, tmp_path, test_data_dir):
        """CLI: Use --save_images flag to save extracted images."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Text", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                           "--save_images", "--backend", "nemoparse",
                           "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        # Just verify the command succeeded
        assert (output_dir / "banyan-extract-output.md").exists()

    def test_cli_with_save_tables_flag(self, tmp_path, test_data_dir):
        """CLI: Use --save_tables flag to save extracted tables."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            # Mock response with a table
            mock_response.return_value = [
                {"type": "table", "text": "| A | B |\n| 1 | 2 |", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                           "--save_tables", "--backend", "nemoparse",
                           "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        assert (output_dir / "banyan-extract-output.md").exists()

    def test_cli_with_save_bbox_data_flag(self, tmp_path, test_data_dir):
        """CLI: Use --save_bbox_data flag to save bounding box data."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Text", "bbox": {"xmin": 10, "ymin": 20, "xmax": 100, "ymax": 50}}
            ]

            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                           "--save_bbox_data", "--backend", "nemoparse",
                           "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        # Bbox data should be saved alongside markdown
        assert (output_dir / "banyan-extract-output.md").exists()

    def test_cli_with_multiple_save_options(self, tmp_path, test_data_dir):
        """CLI: Combine multiple save flags (images, tables, bbox)."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                           "--save_images", "--save_tables", "--save_bbox_data",
                           "--backend", "nemoparse",
                           "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        assert (output_dir / "banyan-extract-output.md").exists()

    def test_cli_directory_with_recursion(self, nested_cli_dir, tmp_path):
        """CLI: Process directory recursively with --recursion_depth."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Nested content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(nested_cli_dir), str(output_dir),
                           "--is_input_dir", "--recursion_depth", "-1",  # Unlimited depth
                           "--backend", "nemoparse",
                           "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        # Verify all files processed (2 root + 2 subdir = 4 files)
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 4, f"Expected 4 output files, got {len(output_files)}"

    def test_cli_with_preserve_structure(self, nested_cli_dir, tmp_path):
        """CLI: Use --preserve_input_structure to maintain directory structure."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Structured content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(nested_cli_dir), str(output_dir),
                           "--is_input_dir", "--preserve_input_structure",
                           "--recursion_depth", "-1",
                           "--backend", "nemoparse",
                           "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        # Verify subdirectory structure preserved
        assert (output_dir / "subdir").exists(), "Subdirectory should be preserved"
        assert len(list((output_dir / "subdir").glob("*.md"))) == 2, "Subdir should have 2 files"

    def test_cli_with_overwrite_flag(self, tmp_path, test_data_dir):
        """CLI: Test --overwrite flag behavior."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing output file
        existing_file = output_dir / "banyan-extract-output.md"
        existing_file.write_text("Old content")

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "New content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            original_argv = sys.argv
            try:
                sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                           "--overwrite", "--backend", "nemoparse",
                           "--endpoint", "http://test:8000", "--model_name", "test-model"]
                cli_main()
            finally:
                sys.argv = original_argv

        # Verify file was overwritten
        assert existing_file.exists()
        content = existing_file.read_text()
        assert "New content" in content

    def test_cli_error_missing_input_file(self, tmp_path):
        """CLI: Handle missing input file with clear error."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        original_argv = sys.argv
        try:
            sys.argv = ["banyan-extract", "/nonexistent/file.pdf", str(output_dir),
                       "--backend", "nemoparse",
                       "--endpoint", "http://test:8000", "--model_name", "test-model"]

            # Should raise SystemExit or FileNotFoundError
            with pytest.raises((SystemExit, FileNotFoundError)):
                cli_main()
        finally:
            sys.argv = original_argv

    def test_cli_error_invalid_backend(self, tmp_path, test_data_dir):
        """CLI: Handle invalid backend selection."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        original_argv = sys.argv
        try:
            sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                       "--backend", "invalid_backend",
                       "--endpoint", "http://test:8000", "--model_name", "test-model"]

            # Should raise SystemExit or ValueError
            with pytest.raises((SystemExit, ValueError)):
                cli_main()
        finally:
            sys.argv = original_argv

    def test_cli_error_missing_endpoint(self, tmp_path, test_data_dir):
        """CLI: Handle missing endpoint configuration."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        original_argv = sys.argv
        try:
            sys.argv = ["banyan-extract", str(test_pdf), str(output_dir),
                       "--backend", "nemoparse",
                       "--config_file", "/nonexistent/.env"]  # Force config to be missing

            # Should raise SystemExit or ValueError
            with pytest.raises((SystemExit, ValueError)):
                cli_main()
        finally:
            sys.argv = original_argv


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
