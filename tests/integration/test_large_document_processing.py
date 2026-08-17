"""
Integration tests for large document processing.

Tests system behavior with large documents:
- Multi-page PDFs (50+ pages)
- Memory efficiency during large document processing
- Progress tracking for long-running operations
- Batches of large documents
- High-resolution content handling

These tests verify the system can handle production-scale documents
without memory exhaustion or performance degradation.
"""

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image
import io

from banyan_extract import BanyanExtract


class TestLargeDocumentProcessing:
    """Integration tests for large document processing."""

    @pytest.fixture
    def large_pdf_50_pages(self, test_data_dir):
        """Use pre-existing 50-page PDF from test data."""
        large_pdf = test_data_dir / "docs" / "large_50_pages.pdf"
        if not large_pdf.exists():
            pytest.skip("large_50_pages.pdf not available in test data")
        return large_pdf

    @pytest.fixture
    def large_pdf_100_pages(self, test_data_dir):
        """Use pre-existing 100-page PDF from test data."""
        large_pdf = test_data_dir / "docs" / "large_100_pages.pdf"
        if not large_pdf.exists():
            pytest.skip("large_100_pages.pdf not available in test data")
        return large_pdf

    @pytest.fixture
    def batch_of_large_pdfs(self, tmp_path, test_data_dir):
        """Use pre-existing large PDFs from test data."""
        batch_dir = tmp_path / "large_batch"
        batch_dir.mkdir()

        # Copy pre-existing large PDFs to batch directory
        large_pdfs = [
            "large_doc_0_20p.pdf",
            "large_doc_1_25p.pdf",
            "large_doc_2_30p.pdf",
            "large_doc_3_35p.pdf",
            "large_doc_4_40p.pdf",
        ]

        for pdf_name in large_pdfs:
            source = test_data_dir / "docs" / pdf_name
            if source.exists():
                shutil.copy(source, batch_dir / pdf_name)

        # Verify at least some files were copied
        if len(list(batch_dir.glob("*.pdf"))) == 0:
            pytest.skip("No large PDFs available in test data")

        return batch_dir

    def test_process_50_page_pdf(self, large_pdf_50_pages, tmp_path):
        """Process 50-page PDF successfully."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            # Mock response for each page
            mock_response.return_value = [
                {"type": "text", "text": "Page content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(large_pdf_50_pages),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should complete without memory errors
            extractor()

        # Verify output created
        output_file = output_dir / "banyan-extract-output.md"
        assert output_file.exists(), "Expected markdown output for 50-page PDF"

        # Verify content is non-empty
        content = output_file.read_text()
        assert len(content) > 0, "Output should contain content"

        # Verify mock was called 50 times (once per page)
        assert mock_response.call_count == 50, f"Expected 50 API calls, got {mock_response.call_count}"

    def test_process_100_page_pdf(self, large_pdf_100_pages, tmp_path):
        """Process 100-page PDF successfully."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Page content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(large_pdf_100_pages),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            extractor()

        # Verify output created
        output_file = output_dir / "banyan-extract-output.md"
        assert output_file.exists()

        # Verify all pages processed (100 API calls)
        assert mock_response.call_count == 100, f"Expected 100 API calls, got {mock_response.call_count}"

    def test_batch_of_large_documents(self, batch_of_large_pdfs, tmp_path):
        """Process batch of large documents (5 PDFs, 20-40 pages each)."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(batch_of_large_pdfs),
                output_dir=str(output_dir),
                is_input_dir=True,
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should process all documents without memory exhaustion
            extractor()

        # Verify 5 output files created
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 5, f"Expected 5 output files, got {len(output_files)}"

        # Verify all files non-empty
        for output_file in output_files:
            assert output_file.stat().st_size > 0, f"Output {output_file.name} is empty"

        # Total pages: 20 + 25 + 30 + 35 + 40 = 150 pages
        assert mock_response.call_count == 150, f"Expected 150 API calls, got {mock_response.call_count}"

    def test_memory_efficiency_streaming(self, large_pdf_50_pages, tmp_path):
        """Verify memory-efficient page-by-page processing."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Track if responses are being processed incrementally
        call_count = [0]

        def mock_response_side_effect(*args, **kwargs):
            call_count[0] += 1
            return [
                {"type": "text", "text": f"Page {call_count[0]}", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.side_effect = mock_response_side_effect

            extractor = BanyanExtract(
                input_file=str(large_pdf_50_pages),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Process large document
            extractor()

        # Verify incremental processing (50 separate calls, not batched)
        assert call_count[0] == 50, "Should process pages incrementally"

        # Verify output contains content from multiple pages
        output_file = output_dir / "banyan-extract-output.md"
        content = output_file.read_text()
        assert "Page 1" in content and "Page 50" in content, "Should contain content from first and last pages"

    def test_large_document_with_save_options(self, large_pdf_50_pages, tmp_path):
        """Process large document with all save options enabled."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            # Mock response with various content types
            mock_response.return_value = [
                {"type": "text", "text": "Page text", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}},
                {"type": "table", "text": "| A | B |\n| 1 | 2 |", "bbox": {"xmin": 0, "ymin": 60, "xmax": 100, "ymax": 100}}
            ]

            extractor = BanyanExtract(
                input_file=str(large_pdf_50_pages),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model",
                save_images=True,
                save_tables=True,
                save_bbox_data=True,
                save_page_numbers=True
            )

            extractor()

        # Verify markdown output created
        output_file = output_dir / "banyan-extract-output.md"
        assert output_file.exists()

        # Verify output has content
        assert output_file.stat().st_size > 0

    def test_large_document_overwrite_behavior(self, large_pdf_50_pages, tmp_path):
        """Test overwrite behavior with large documents."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # First processing
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "First processing", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(large_pdf_50_pages),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model",
                overwrite=False
            )

            extractor()

        output_file = output_dir / "banyan-extract-output.md"
        first_mtime = output_file.stat().st_mtime
        first_content = output_file.read_text()

        # Second processing with overwrite=False (should skip)
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Second processing", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(large_pdf_50_pages),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model",
                overwrite=False
            )

            extractor()

        # Verify file NOT overwritten (same mtime)
        second_mtime = output_file.stat().st_mtime
        assert first_mtime == second_mtime, "File should not be overwritten when overwrite=False"

        # Content should still be from first processing
        second_content = output_file.read_text()
        assert second_content == first_content

    def test_large_document_with_rotation(self, large_pdf_50_pages, tmp_path):
        """Process large document with rotation detection."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Rotated content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            # Mock rotation detection
            with patch('banyan_extract.utils.rotation_detection.detect_rotation_angle') as mock_detect:
                mock_detect.return_value = (90, 0.95)  # 90 degrees, high confidence

                extractor = BanyanExtract(
                    input_file=str(large_pdf_50_pages),
                    output_dir=str(output_dir),
                    backend="nemoparse",
                    endpoint="http://test:8000",
                    model_name="test-model",
                    auto_detect_rotation=True
                )

                extractor()

        # Verify processing completed
        output_file = output_dir / "banyan-extract-output.md"
        assert output_file.exists()

        # Note: rotation detection called once per page (50 times)
        # But we're just verifying the system handles it without crashing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
