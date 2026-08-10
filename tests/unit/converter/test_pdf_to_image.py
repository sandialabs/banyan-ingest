"""
Tests for PDF to image conversion functions.

Tests the convert_bytes_to_images function which converts PDF byte streams
to lists of PIL Image objects.
"""

import pytest
from io import BytesIO
from pathlib import Path
from PIL import Image

from banyan_extract.converter.pdf_to_image import (
    convert_bytes_to_images,
    convert_pdf_to_images
)


class TestConvertBytesToImages:
    """Tests for convert_bytes_to_images function."""

    def test_single_page_pdf(self, test_data_dir):
        """Test conversion of single-page PDF from bytes."""
        # Load a real PDF file
        pdf_path = test_data_dir / "docs" / "sample.pdf"
        pdf_bytes = pdf_path.read_bytes()
        byte_stream = BytesIO(pdf_bytes)

        result = convert_bytes_to_images(byte_stream)

        # Should return list of PIL Images
        assert isinstance(result, list)
        assert len(result) == 1  # sample.pdf has 1 page
        assert isinstance(result[0], Image.Image)

    def test_multi_page_pdf(self, test_data_dir):
        """Test conversion of multi-page PDF from bytes."""
        # Check if we have a multi-page PDF, otherwise use single page
        pdf_path = test_data_dir / "docs" / "sample_rotation.pdf"
        if not pdf_path.exists():
            pdf_path = test_data_dir / "docs" / "sample.pdf"

        pdf_bytes = pdf_path.read_bytes()
        byte_stream = BytesIO(pdf_bytes)

        result = convert_bytes_to_images(byte_stream)

        # Should return list of PIL Images
        assert isinstance(result, list)
        assert len(result) >= 1
        for img in result:
            assert isinstance(img, Image.Image)

    def test_custom_dpi_default(self, test_data_dir):
        """Test conversion with default DPI (200)."""
        pdf_path = test_data_dir / "docs" / "sample.pdf"
        pdf_bytes = pdf_path.read_bytes()
        byte_stream = BytesIO(pdf_bytes)

        result = convert_bytes_to_images(byte_stream)

        assert len(result) == 1
        # Image should have reasonable dimensions for 200 DPI
        width, height = result[0].size
        assert width > 0
        assert height > 0

    def test_custom_dpi_higher(self, test_data_dir):
        """Test conversion with higher DPI produces larger image."""
        pdf_path = test_data_dir / "docs" / "sample.pdf"
        pdf_bytes = pdf_path.read_bytes()

        # Convert with default DPI (200)
        byte_stream_200 = BytesIO(pdf_bytes)
        result_200 = convert_bytes_to_images(byte_stream_200, dpi=200)

        # Convert with higher DPI (300)
        byte_stream_300 = BytesIO(pdf_bytes)
        result_300 = convert_bytes_to_images(byte_stream_300, dpi=300)

        # Higher DPI should produce larger image
        width_200, height_200 = result_200[0].size
        width_300, height_300 = result_300[0].size

        assert width_300 > width_200
        assert height_300 > height_200

    def test_invalid_pdf_bytes(self):
        """Test handling of invalid PDF bytes."""
        invalid_bytes = b"This is not a PDF file"
        byte_stream = BytesIO(invalid_bytes)

        # Should raise an exception (pymupdf.FileDataError or similar)
        with pytest.raises(Exception):
            convert_bytes_to_images(byte_stream)

    def test_empty_byte_stream(self):
        """Test handling of empty byte stream."""
        empty_stream = BytesIO(b"")

        # Should raise an exception
        with pytest.raises(Exception):
            convert_bytes_to_images(empty_stream)

    def test_returns_pil_images(self, test_data_dir):
        """Test that returned images are PIL Image objects with correct properties."""
        pdf_path = test_data_dir / "docs" / "sample.pdf"
        pdf_bytes = pdf_path.read_bytes()
        byte_stream = BytesIO(pdf_bytes)

        result = convert_bytes_to_images(byte_stream)

        # Check first image properties
        img = result[0]
        assert hasattr(img, 'size')
        assert hasattr(img, 'mode')
        assert hasattr(img, 'format')

        # Image should have RGB mode (typical for PDF rendering)
        assert img.mode in ['RGB', 'RGBA', 'L']

        # Should be able to save the image
        output = BytesIO()
        img.save(output, format='PNG')
        assert output.tell() > 0  # Should have written some data

    def test_byte_stream_position_independent(self, test_data_dir):
        """Test that function works regardless of byte stream position."""
        pdf_path = test_data_dir / "docs" / "sample.pdf"
        pdf_bytes = pdf_path.read_bytes()

        # Create stream and read some bytes (move position)
        byte_stream = BytesIO(pdf_bytes)
        byte_stream.read(100)  # Move position forward

        # Function should still work (pymupdf handles stream position)
        result = convert_bytes_to_images(byte_stream)

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_multiple_conversions_same_bytes(self, test_data_dir):
        """Test converting the same PDF bytes multiple times."""
        pdf_path = test_data_dir / "docs" / "sample.pdf"
        pdf_bytes = pdf_path.read_bytes()

        # Convert twice with new streams
        stream1 = BytesIO(pdf_bytes)
        result1 = convert_bytes_to_images(stream1)

        stream2 = BytesIO(pdf_bytes)
        result2 = convert_bytes_to_images(stream2)

        # Results should be equivalent
        assert len(result1) == len(result2)
        assert result1[0].size == result2[0].size


class TestConvertPdfToImages:
    """Tests for convert_pdf_to_images function (file path variant)."""

    def test_file_path_conversion(self, test_data_dir):
        """Test conversion from file path."""
        pdf_path = test_data_dir / "docs" / "sample.pdf"

        result = convert_pdf_to_images(str(pdf_path))

        assert isinstance(result, list)
        assert len(result) >= 1
        assert isinstance(result[0], Image.Image)

    def test_file_path_with_custom_dpi(self, test_data_dir):
        """Test file path conversion with custom DPI."""
        pdf_path = test_data_dir / "docs" / "sample.pdf"

        result = convert_pdf_to_images(str(pdf_path), dpi=150)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert isinstance(result[0], Image.Image)

    def test_nonexistent_file(self):
        """Test handling of nonexistent file."""
        fake_path = "/nonexistent/path/to/file.pdf"

        with pytest.raises(Exception):
            convert_pdf_to_images(fake_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
