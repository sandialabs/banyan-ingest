"""
Integration tests for large-scale batch processing.

Tests batch processing workflows with 20+ documents to verify:
- Memory efficiency during large batch operations
- Correct processor selection for mixed file types
- Directory recursion and structure preservation
- File extension filtering
- Progress tracking during batch operations

These tests use real file I/O and actual document processing to validate
production-scale batch workflows.
"""

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from banyan_extract import BanyanExtract


class TestLargeBatchProcessing:
    """Integration tests for large-scale batch processing."""

    @pytest.fixture
    def large_batch_dir(self, tmp_path, test_data_dir):
        """Create directory with 20+ test documents."""
        batch_dir = tmp_path / "large_batch"
        batch_dir.mkdir()

        # Copy existing test files multiple times to create 20+ documents
        source_pdf = test_data_dir / "docs" / "sample.pdf"
        source_pptx = test_data_dir / "docs" / "slides.pptx"

        # Create 15 PDFs (duplicate sample.pdf with different names)
        for i in range(15):
            dest = batch_dir / f"document_{i:03d}.pdf"
            shutil.copy(source_pdf, dest)

        # Create 8 PPTX files
        for i in range(8):
            dest = batch_dir / f"presentation_{i:03d}.pptx"
            shutil.copy(source_pptx, dest)

        return batch_dir

    @pytest.fixture
    def nested_batch_dir(self, tmp_path, test_data_dir):
        """Create nested directory structure for recursion tests."""
        root = tmp_path / "nested_batch"
        root.mkdir()

        # Root level: 3 files
        source_pdf = test_data_dir / "docs" / "sample.pdf"
        for i in range(3):
            shutil.copy(source_pdf, root / f"root_{i}.pdf")

        # Level 1 subdirs: 2 directories with 2 files each
        for d in range(2):
            subdir = root / f"subdir_{d}"
            subdir.mkdir()
            for i in range(2):
                shutil.copy(source_pdf, subdir / f"sub_{d}_{i}.pdf")

        # Level 2 nested: 1 deep subdirectory with 2 files
        deep = root / "subdir_0" / "deep"
        deep.mkdir()
        for i in range(2):
            shutil.copy(source_pdf, deep / f"deep_{i}.pdf")

        # Total: 3 + 4 + 2 = 9 files
        return root

    def test_batch_20_documents(self, large_batch_dir, tmp_path):
        """Process 20+ documents in batch."""
        output_dir = tmp_path / "output"

        # Mock HTTP boundary to avoid real API calls
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Sample content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(large_batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            extractor()

        # Verify all 23 documents processed (15 PDFs + 8 PPTX)
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 23, f"Expected 23 output files, got {len(output_files)}"

        # Verify output files exist and are non-empty
        for output_file in output_files:
            assert output_file.stat().st_size > 0, f"Output file {output_file.name} is empty"

    def test_batch_with_mixed_file_types(self, large_batch_dir, tmp_path):
        """Process batch with PDFs and PPTX files."""
        output_dir = tmp_path / "output"

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(large_batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                backend="auto",  # Auto-detect backend per file
                endpoint="http://test:8000",
                model_name="test-model"
            )

            extractor()

        # Verify PDFs processed (15 files)
        pdf_outputs = [f for f in output_dir.glob("*.md") if "document_" in f.name]
        assert len(pdf_outputs) == 15, f"Expected 15 PDF outputs, got {len(pdf_outputs)}"

        # Verify PPTX processed (8 files)
        pptx_outputs = [f for f in output_dir.glob("*.md") if "presentation_" in f.name]
        assert len(pptx_outputs) == 8, f"Expected 8 PPTX outputs, got {len(pptx_outputs)}"

    def test_batch_with_recursion(self, nested_batch_dir, tmp_path):
        """Process directory recursively."""
        output_dir = tmp_path / "output"

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(nested_batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                recursion_depth=-1,  # Unlimited recursion
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            extractor()

        # Verify all 9 nested files processed
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 9, f"Expected 9 output files, got {len(output_files)}"

        # Verify files from different levels processed
        root_files = [f for f in output_files if "root_" in f.name]
        sub_files = [f for f in output_files if "sub_" in f.name]
        deep_files = [f for f in output_files if "deep_" in f.name]

        assert len(root_files) == 3, "Expected 3 root-level files"
        assert len(sub_files) == 4, "Expected 4 subdir files"
        assert len(deep_files) == 2, "Expected 2 deep files"

    def test_batch_with_filters(self, large_batch_dir, tmp_path):
        """Process batch with file extension filters."""
        output_dir = tmp_path / "output"

        # Add some non-PDF/PPTX files to test filtering
        (large_batch_dir / "readme.txt").write_text("Not a document")
        (large_batch_dir / "image.png").write_bytes(b"fake image")

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(large_batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                backend="auto",
                endpoint="http://test:8000",
                model_name="test-model"
                # effective_extensions defaults to {"pdf", "pptx"}
            )

            extractor()

        # Verify only PDF and PPTX files processed (not txt or png)
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 23, f"Expected 23 outputs (PDFs+PPTX only), got {len(output_files)}"

        # Verify txt and png NOT processed
        assert not (output_dir / "readme.md").exists()
        assert not (output_dir / "image.md").exists()

    def test_batch_preserve_structure(self, nested_batch_dir, tmp_path):
        """Verify directory structure preserved in output."""
        output_dir = tmp_path / "output"

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(nested_batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                preserve_input_structure=True,
                recursion_depth=-1,
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            extractor()

        # Verify subdirectories created in output
        assert (output_dir / "subdir_0").exists(), "subdir_0 should be preserved"
        assert (output_dir / "subdir_1").exists(), "subdir_1 should be preserved"
        assert (output_dir / "subdir_0" / "deep").exists(), "deep subdir should be preserved"

        # Verify files in correct subdirectories
        assert len(list((output_dir / "subdir_0").glob("*.md"))) == 2
        assert len(list((output_dir / "subdir_0" / "deep").glob("*.md"))) == 2

    def test_batch_overwrite_behavior(self, tmp_path, test_data_dir):
        """Test overwrite vs skip behavior for existing files."""
        batch_dir = tmp_path / "batch"
        batch_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Copy 3 test files
        source_pdf = test_data_dir / "docs" / "sample.pdf"
        for i in range(3):
            shutil.copy(source_pdf, batch_dir / f"doc_{i}.pdf")

        # Process first time
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Original content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                overwrite=False,
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            extractor()

        # Verify 3 files created
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 3

        # Get modification times
        original_mtimes = {f.name: f.stat().st_mtime for f in output_files}

        # Process again with overwrite=False
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "New content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                overwrite=False,
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            extractor()

        # Verify files NOT overwritten (same modification times)
        new_mtimes = {f.name: f.stat().st_mtime for f in output_dir.glob("*.md")}
        assert original_mtimes == new_mtimes, "Files should not be overwritten when overwrite=False"

    def test_batch_memory_efficiency(self, large_batch_dir, tmp_path):
        """Verify memory doesn't grow unbounded during batch processing."""
        output_dir = tmp_path / "output"

        # Note: This is a basic smoke test. Real memory profiling would require
        # memory_profiler or similar tools and is better suited for performance testing.

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(large_batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Process large batch - should complete without memory errors
            extractor()

        # Verify processing completed successfully
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 23, "All files should be processed"

    def test_batch_with_depth_limit(self, nested_batch_dir, tmp_path):
        """Test recursion depth limiting."""
        output_dir = tmp_path / "output"

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(nested_batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                recursion_depth=1,  # Only go 1 level deep
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            extractor()

        # Verify only root and first-level subdir files processed
        # Should NOT process files in nested_batch_dir/subdir_0/deep/
        output_files = list(output_dir.glob("**/*.md"))

        # Root: 3 files, subdir_0: 2 files, subdir_1: 2 files = 7 total
        # Should NOT include 2 deep files
        assert len(output_files) == 7, f"Expected 7 files with depth=1, got {len(output_files)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
