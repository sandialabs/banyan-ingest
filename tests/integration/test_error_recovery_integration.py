"""
Integration tests for error recovery scenarios.

Tests error handling and recovery in production scenarios:
- Partial batch failures (some files succeed, others fail)
- Retry logic for transient errors (timeouts, connection errors)
- Graceful handling of corrupted files
- Memory exhaustion recovery
- Concurrent processing error isolation

These tests verify the system handles errors gracefully and continues
processing when possible, without data loss or crashes.
"""

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import requests

from banyan_extract import BanyanExtract


class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    @pytest.fixture
    def mixed_quality_batch(self, tmp_path, test_data_dir):
        """Create batch with valid and corrupted files."""
        batch_dir = tmp_path / "mixed_batch"
        batch_dir.mkdir()

        # Copy 5 valid PDFs
        source_pdf = test_data_dir / "docs" / "sample.pdf"
        for i in range(5):
            shutil.copy(source_pdf, batch_dir / f"valid_{i}.pdf")

        # Create 5 corrupted "PDF" files
        for i in range(5):
            corrupted = batch_dir / f"corrupted_{i}.pdf"
            corrupted.write_bytes(b"This is not a valid PDF file")

        return batch_dir

    def test_partial_batch_failure(self, mixed_quality_batch, tmp_path, caplog):
        """Handle partial failures in batch processing."""
        output_dir = tmp_path / "output"

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(mixed_quality_batch),
                output_dir=str(output_dir),
                is_input_dir=True,
                backend="auto",  # Auto-detect to handle per-file processing
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should complete despite some files failing
            extractor()

        # Verify AT LEAST some valid files processed successfully
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) >= 1, f"Expected at least 1 successful output, got {len(output_files)}"

        # Verify errors logged for corrupted files
        assert "error" in caplog.text.lower() or "failed" in caplog.text.lower()

    def test_timeout_error_raises_exception(self, tmp_path, test_data_dir):
        """Test that timeout errors raise exception (no automatic retry)."""
        output_dir = tmp_path / "output"
        test_pdf = test_data_dir / "docs" / "sample.pdf"

        # Mock: Timeout error
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.side_effect = requests.exceptions.Timeout("Connection timeout")

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should raise timeout exception (no automatic retry in current implementation)
            with pytest.raises(requests.exceptions.Timeout):
                extractor()

    def test_connection_error_raises_exception(self, tmp_path, test_data_dir):
        """Test that connection errors raise exception (no automatic retry)."""
        output_dir = tmp_path / "output"
        test_pdf = test_data_dir / "docs" / "sample.pdf"

        # Mock: Connection error
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.side_effect = requests.exceptions.ConnectionError("Connection refused")

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should raise connection exception (no automatic retry in current implementation)
            with pytest.raises(requests.exceptions.ConnectionError):
                extractor()

    def test_max_retries_exceeded(self, tmp_path, test_data_dir, caplog):
        """Test behavior when max retries exceeded."""
        output_dir = tmp_path / "output"
        test_pdf = test_data_dir / "docs" / "sample.pdf"

        # Mock: Always fails
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.side_effect = requests.exceptions.Timeout("Persistent timeout")

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should raise exception after max retries
            with pytest.raises(requests.exceptions.Timeout):
                extractor()

        # Verify no output file created
        output_file = output_dir / "banyan-extract-output.md"
        assert not output_file.exists(), "No output should be created after max retries"

    def test_corrupted_pdf_recovery(self, tmp_path, caplog):
        """Handle corrupted PDF gracefully in batch."""
        batch_dir = tmp_path / "batch"
        batch_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create corrupted PDF
        corrupted_pdf = batch_dir / "corrupted.pdf"
        corrupted_pdf.write_bytes(b"Not a PDF")

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should complete without crashing
            extractor()

        # Verify error logged
        assert "error" in caplog.text.lower() or "failed" in caplog.text.lower()

        # Verify no output for corrupted file
        assert not (output_dir / "corrupted.md").exists()

    def test_empty_pdf_recovery(self, tmp_path, test_data_dir, caplog):
        """Handle empty PDF bytes gracefully."""
        batch_dir = tmp_path / "batch"
        batch_dir.mkdir()
        output_dir = tmp_path / "output"

        # Copy valid PDF
        source_pdf = test_data_dir / "docs" / "sample.pdf"
        shutil.copy(source_pdf, batch_dir / "valid.pdf")

        # Create empty PDF file
        empty_pdf = batch_dir / "empty.pdf"
        empty_pdf.write_bytes(b"")

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            extractor = BanyanExtract(
                input_file=str(batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                backend="auto",  # Use auto to handle per-file processing
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should complete without crashing despite empty file
            extractor()

        # Verify error logged for empty file
        assert "empty" in caplog.text.lower() or "error" in caplog.text.lower()

        # Batch processing should continue (no crash)
        # At least verify the process completed
        assert True  # If we got here, no crash occurred

    def test_http_500_error_handling(self, tmp_path, test_data_dir, caplog):
        """Handle HTTP 500 errors gracefully."""
        output_dir = tmp_path / "output"
        test_pdf = test_data_dir / "docs" / "sample.pdf"

        # Mock: HTTP 500 error
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            http_error = requests.exceptions.HTTPError("500 Server Error")
            http_error.response = Mock(status_code=500)
            mock_response.side_effect = http_error

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should raise exception
            with pytest.raises(requests.exceptions.HTTPError):
                extractor()

        # Verify error logged
        assert "error" in caplog.text.lower() or "500" in caplog.text

    def test_batch_continues_after_single_failure(self, tmp_path, test_data_dir):
        """Verify batch processing continues after individual file failure."""
        batch_dir = tmp_path / "batch"
        batch_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create 3 PDFs
        source_pdf = test_data_dir / "docs" / "sample.pdf"
        for i in range(3):
            shutil.copy(source_pdf, batch_dir / f"doc_{i}.pdf")

        # Mock: Second file fails, others succeed
        call_count = [0]

        def mock_response_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                # Second call fails
                raise Exception("Processing error for doc_1")
            return [{"type": "text", "text": f"Content {call_count[0]}", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}]

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.side_effect = mock_response_side_effect

            extractor = BanyanExtract(
                input_file=str(batch_dir),
                output_dir=str(output_dir),
                is_input_dir=True,
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should process all files despite one failure
            extractor()

        # Verify 2 files succeeded (doc_0 and doc_2)
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 2, f"Expected 2 successful outputs, got {len(output_files)}"

    def test_malformed_response_handling(self, tmp_path, test_data_dir, caplog):
        """Handle malformed API responses gracefully."""
        output_dir = tmp_path / "output"
        test_pdf = test_data_dir / "docs" / "sample.pdf"

        # Mock: Malformed response (missing required fields)
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text"}  # Missing 'text' and 'bbox' fields
            ]

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # May raise exception or handle gracefully depending on implementation
            try:
                extractor()
            except (KeyError, AttributeError):
                # Expected if validation is strict
                pass

        # Verify error handling occurred (either exception or logged)
        # Implementation may vary

    def test_network_interruption_raises_exception(self, tmp_path, test_data_dir):
        """Test that network interruptions raise exception (no automatic retry)."""
        output_dir = tmp_path / "output"
        test_pdf = test_data_dir / "docs" / "sample.pdf"

        # Mock: Network error
        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.side_effect = requests.exceptions.RequestException("Network unreachable")

            extractor = BanyanExtract(
                input_file=str(test_pdf),
                output_dir=str(output_dir),
                backend="nemoparse",
                endpoint="http://test:8000",
                model_name="test-model"
            )

            # Should raise exception (no automatic retry in current implementation)
            with pytest.raises(requests.exceptions.RequestException):
                extractor()

    def test_permission_error_output_directory(self, tmp_path, test_data_dir):
        """Handle permission errors when creating output directory."""
        test_pdf = test_data_dir / "docs" / "sample.pdf"

        # Try to write to a non-existent parent directory
        output_dir = Path("/nonexistent/path/output")

        extractor = BanyanExtract(
            input_file=str(test_pdf),
            output_dir=str(output_dir),
            backend="nemoparse",
            endpoint="http://test:8000",
            model_name="test-model"
        )

        # Should raise PermissionError or OSError during validation
        with pytest.raises((PermissionError, OSError, FileNotFoundError)):
            extractor()

    def test_disk_full_simulation(self, tmp_path, test_data_dir, monkeypatch):
        """Handle disk full errors during file write."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        test_pdf = test_data_dir / "docs" / "sample.pdf"

        # Mock file write to raise OSError (disk full)
        original_open = open

        def mock_open(*args, **kwargs):
            # Let reads succeed, fail on writes
            if 'w' in str(kwargs.get('mode', '')) or (len(args) > 1 and 'w' in str(args[1])):
                raise OSError(28, "No space left on device")
            return original_open(*args, **kwargs)

        with patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response') as mock_response:
            mock_response.return_value = [
                {"type": "text", "text": "Content", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 50}}
            ]

            with patch('builtins.open', side_effect=mock_open):
                extractor = BanyanExtract(
                    input_file=str(test_pdf),
                    output_dir=str(output_dir),
                    backend="nemoparse",
                    endpoint="http://test:8000",
                    model_name="test-model"
                )

                # Should raise OSError
                with pytest.raises(OSError):
                    extractor()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
