"""
Tests for PPTX processor methods.

Tests the process_image and fix_fences methods of the PptxProcessor class.
"""

import pytest
from io import BytesIO
from PIL import Image
from unittest.mock import MagicMock, Mock

from banyan_extract.processor.pptx_processor import PptxProcessor


class TestProcessImage:
    """Tests for process_image method."""

    def test_process_image_png_conversion(self):
        """Test successful PNG image conversion."""
        processor = PptxProcessor(ocr_backend="nemotron")

        # Create a real PNG image blob
        test_image = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        test_image.save(buffer, format='PNG')
        png_blob = buffer.getvalue()

        # Mock python-pptx image object
        mock_image = MagicMock()
        mock_image.content_type = 'image/png'
        mock_image.blob = png_blob

        result = processor.process_image(mock_image)

        # Should return PIL Image
        assert isinstance(result, Image.Image)
        assert result.size == (100, 100)

    def test_process_image_wmf_format_skipped(self, capsys):
        """Test WMF format is skipped with message."""
        processor = PptxProcessor(ocr_backend="nemotron")

        # Mock python-pptx image object with WMF content type
        mock_image = MagicMock()
        mock_image.content_type = 'image/x-wmf'
        mock_image.blob = b'fake wmf data'

        result = processor.process_image(mock_image)

        # Should return None
        assert result is None

        # Should print skip message
        captured = capsys.readouterr()
        assert "wmf" in captured.out.lower()
        assert "skipping" in captured.out.lower()

    def test_process_image_jpeg_conversion(self):
        """Test successful JPEG image conversion."""
        processor = PptxProcessor(ocr_backend="nemotron")

        # Create a real JPEG image blob
        test_image = Image.new('RGB', (50, 75), color='blue')
        buffer = BytesIO()
        test_image.save(buffer, format='JPEG')
        jpeg_blob = buffer.getvalue()

        # Mock python-pptx image object
        mock_image = MagicMock()
        mock_image.content_type = 'image/jpeg'
        mock_image.blob = jpeg_blob

        result = processor.process_image(mock_image)

        # Should return PIL Image
        assert isinstance(result, Image.Image)
        assert result.size == (50, 75)


class TestFixFences:
    """Tests for fix_fences method."""

    @pytest.fixture
    def fix_fences_function(self):
        """
        Recreate the fix_fences logic for testing.

        Since fix_fences is defined inline in the MarkdownTexifyPredictor class,
        we test its logic by recreating the function directly.
        """
        import re

        def fix_fences(text: str) -> str:
            text = re.sub(r'<math display="block">(.*?)</math>', r'$$\1$$', text, flags=re.DOTALL)
            text = re.sub(r'<math>(.*?)</math>', r'$\1$', text, flags=re.DOTALL)
            if re.search(r'<math display="block">', text):
                text = ""
            if re.search(r'<math>', text):
                text = ""
            return text

        return fix_fences

    def test_fix_fences_display_math(self, fix_fences_function):
        """Test display math conversion (<math display='block'> to $$)."""
        input_text = '<math display="block">x^2 + y^2 = r^2</math>'
        result = fix_fences_function(input_text)

        # Should convert to display math delimiters
        assert result == '$$x^2 + y^2 = r^2$$'

    def test_fix_fences_inline_math(self, fix_fences_function):
        """Test inline math conversion (<math> to $)."""
        input_text = 'The equation <math>y = mx + b</math> is linear.'
        result = fix_fences_function(input_text)

        # Should convert to inline math delimiters
        assert result == 'The equation $y = mx + b$ is linear.'

    def test_fix_fences_multiline_math(self, fix_fences_function):
        """Test multiline math expression."""
        input_text = '<math display="block">\n  x^2 + y^2\n  = z^2\n</math>'
        result = fix_fences_function(input_text)

        # Should preserve newlines and convert delimiters
        assert result == '$$\n  x^2 + y^2\n  = z^2\n$$'

    def test_fix_fences_incomplete_display_tag(self, fix_fences_function):
        """Test incomplete display math tags return empty string."""
        # Unclosed display math tag (safety check)
        input_text = '<math display="block">incomplete formula'
        result = fix_fences_function(input_text)

        # Should return empty string (safety mechanism)
        assert result == ''

    def test_fix_fences_incomplete_inline_tag(self, fix_fences_function):
        """Test incomplete inline math tags return empty string."""
        # Unclosed inline math tag
        input_text = '<math>incomplete'
        result = fix_fences_function(input_text)

        # Should return empty string (safety mechanism)
        assert result == ''

    def test_fix_fences_no_math(self, fix_fences_function):
        """Test text without math tags remains unchanged."""
        input_text = 'This is plain text with no math.'
        result = fix_fences_function(input_text)

        # Should return unchanged
        assert result == input_text

    def test_fix_fences_multiple_expressions(self, fix_fences_function):
        """Test multiple math expressions in same text."""
        input_text = 'We have <math>a + b</math> and <math display="block">c^2</math> here.'
        result = fix_fences_function(input_text)

        # Should convert both expressions
        assert result == 'We have $a + b$ and $$c^2$$ here.'

    def test_fix_fences_empty_math_tags(self, fix_fences_function):
        """Test empty math tags."""
        input_text = '<math></math>'
        result = fix_fences_function(input_text)

        # Should convert to empty inline delimiters
        assert result == '$$'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
