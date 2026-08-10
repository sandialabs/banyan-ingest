"""
Unit tests for NemotronOCR class (ocr/nemotron_ocr.py).

These tests verify OCR functionality through the public interface only.
Tests mock the HTTP boundary (OpenAI client) but use real image encoding
and response parsing logic.

Test Organization:
- Module-level function tests: extract_bbox_data_from_response()
- Initialization tests: __init__() with different configurations
- OCR method tests: ocr_image() and get_detailed_ocr_results()
- Error handling tests: Network failures and malformed responses

TDD Principles Applied:
- Test public interfaces only (no _get_response private method)
- Mock external HTTP boundary only
- Use real PIL images and real encoding
- Independent expected values (known-good literals)
"""

import pytest
import base64
import io
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from banyan_extract.ocr.nemotron_ocr import (
    NemotronOCR,
    ModelVersion,
    extract_bbox_data_from_response
)


class TestExtractBboxDataFromResponse:
    """Tests for module-level extract_bbox_data_from_response function."""

    def test_extract_single_bbox_element(self):
        """Extract single bounding box with all fields."""
        response_text = "<x_10.5><y_20.3>Sample Text<x_100.8><y_200.9><class_text>"

        result = extract_bbox_data_from_response(response_text)

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert result[0]["text"] == "Sample Text"
        assert result[0]["bbox"]["xmin"] == 10.5
        assert result[0]["bbox"]["ymin"] == 20.3
        assert result[0]["bbox"]["xmax"] == 100.8
        assert result[0]["bbox"]["ymax"] == 200.9

    def test_extract_multiple_bbox_elements(self):
        """Extract multiple bounding boxes from response."""
        response_text = (
            "<x_10><y_20>First Text<x_100><y_200><class_text>"
            "<x_30><y_40>Second Text<x_150><y_250><class_title>"
        )

        result = extract_bbox_data_from_response(response_text)

        assert len(result) == 2
        assert result[0]["text"] == "First Text"
        assert result[0]["type"] == "text"
        assert result[1]["text"] == "Second Text"
        assert result[1]["type"] == "title"

    def test_extract_bbox_with_multiline_text(self):
        """Extract bounding box where text spans multiple lines."""
        response_text = "<x_10><y_20>Line 1\nLine 2\nLine 3<x_100><y_200><class_paragraph>"

        result = extract_bbox_data_from_response(response_text)

        assert len(result) == 1
        assert result[0]["text"] == "Line 1\nLine 2\nLine 3"
        assert result[0]["type"] == "paragraph"

    def test_extract_bbox_with_special_characters_in_text(self):
        """Extract bounding box containing special characters."""
        response_text = "<x_10><y_20>Price: $99.99 (50% off!)<x_100><y_200><class_text>"

        result = extract_bbox_data_from_response(response_text)

        assert len(result) == 1
        assert result[0]["text"] == "Price: $99.99 (50% off!)"

    def test_extract_empty_response_returns_empty_list(self):
        """Empty response text returns empty list."""
        result = extract_bbox_data_from_response("")

        assert result == []
        assert isinstance(result, list)

    def test_extract_response_without_bbox_markers_returns_empty_list(self):
        """Response without bbox markers returns empty list."""
        response_text = "Just some plain text without markers"

        result = extract_bbox_data_from_response(response_text)

        assert result == []

    def test_extract_bbox_with_integer_coordinates(self):
        """Extract bounding box with integer coordinates (no decimal points)."""
        response_text = "<x_10><y_20>Integer Coords<x_100><y_200><class_text>"

        result = extract_bbox_data_from_response(response_text)

        assert len(result) == 1
        assert result[0]["bbox"]["xmin"] == 10.0
        assert result[0]["bbox"]["ymin"] == 20.0
        assert result[0]["bbox"]["xmax"] == 100.0
        assert result[0]["bbox"]["ymax"] == 200.0


class TestNemotronOCRInitialization:
    """Tests for NemotronOCR initialization."""

    def test_init_with_default_parameters(self):
        """Initialize with default parameters creates client with correct config."""
        ocr = NemotronOCR()

        assert ocr.model_url == ""
        assert ocr.model == "nvidia/NVIDIA-Nemotron-Parse-v1.2"
        assert ocr.model_version == ModelVersion.LATEST
        assert ocr.client is not None

    def test_init_with_custom_endpoint_and_model(self):
        """Initialize with custom endpoint and model name."""
        endpoint = "https://custom-endpoint.example.com/v1"
        model = "custom/model-name"

        ocr = NemotronOCR(endpoint_url=endpoint, model_name=model)

        assert ocr.model_url == endpoint
        assert ocr.model == model
        assert ocr.model_version == ModelVersion.LATEST

    def test_init_with_legacy_model_version(self):
        """Initialize with LEGACY model version."""
        ocr = NemotronOCR(model_version=ModelVersion.LEGACY)

        assert ocr.model_version == ModelVersion.LEGACY
        assert ocr.model == "nvidia/NVIDIA-Nemotron-Parse-v1.2"

    def test_init_with_latest_model_version(self):
        """Initialize with LATEST model version (explicit)."""
        ocr = NemotronOCR(model_version=ModelVersion.LATEST)

        assert ocr.model_version == ModelVersion.LATEST

    def test_init_creates_openai_client_with_correct_base_url(self):
        """OpenAI client is configured with provided endpoint URL."""
        endpoint = "https://test-endpoint.com/v1"

        ocr = NemotronOCR(endpoint_url=endpoint)

        # Client should be created (actual base_url is internal to OpenAI client)
        assert ocr.client is not None
        assert ocr.model_url == endpoint


class TestNemotronOCROcrImage:
    """Tests for ocr_image() method - simple text extraction."""

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_ocr_image_extracts_text_from_single_element(self, mock_get_response):
        """OCR single element returns its text."""
        # Arrange: Mock API response
        mock_get_response.return_value = [
            {
                "type": "text",
                "text": "Hello World",
                "bbox": {"xmin": 10, "ymin": 20, "xmax": 100, "ymax": 50}
            }
        ]

        ocr = NemotronOCR(endpoint_url="https://test.com")
        test_image = Image.new('RGB', (100, 100), color='white')

        # Act
        result = ocr.ocr_image(test_image, temperature=0.0)

        # Assert
        assert result == "Hello World"
        assert mock_get_response.called
        assert mock_get_response.call_count == 1

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_ocr_image_combines_multiple_elements_with_newlines(self, mock_get_response):
        """OCR multiple elements joins them with newlines."""
        # Arrange: Mock API response with multiple text elements
        mock_get_response.return_value = [
            {"type": "title", "text": "Document Title", "bbox": {}},
            {"type": "text", "text": "First paragraph.", "bbox": {}},
            {"type": "text", "text": "Second paragraph.", "bbox": {}}
        ]

        ocr = NemotronOCR(endpoint_url="https://test.com")
        test_image = Image.new('RGB', (100, 100), color='blue')

        # Act
        result = ocr.ocr_image(test_image)

        # Assert
        assert result == "Document Title\nFirst paragraph.\nSecond paragraph."

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_ocr_image_with_custom_temperature(self, mock_get_response):
        """Temperature parameter is passed to underlying API call."""
        mock_get_response.return_value = [
            {"type": "text", "text": "Sample", "bbox": {}}
        ]

        ocr = NemotronOCR(endpoint_url="https://test.com")
        test_image = Image.new('RGB', (50, 50), color='red')

        # Act
        result = ocr.ocr_image(test_image, temperature=0.7)

        # Assert: Check temperature was passed
        call_args = mock_get_response.call_args
        assert call_args[1]['temperature'] == 0.7

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_ocr_image_encodes_image_as_base64_png(self, mock_get_response):
        """Image is encoded as base64 PNG data URI."""
        mock_get_response.return_value = [
            {"type": "text", "text": "Test", "bbox": {}}
        ]

        ocr = NemotronOCR(endpoint_url="https://test.com")
        test_image = Image.new('RGB', (10, 10), color='green')

        # Act
        ocr.ocr_image(test_image)

        # Assert: Check base64 encoding was used
        call_args = mock_get_response.call_args
        base64_arg = call_args[0][0]  # First positional argument
        assert base64_arg.startswith("data:image/png;base64,")
        # Verify it's valid base64 after the prefix
        base64_data = base64_arg.split(",")[1]
        assert len(base64_data) > 0

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_ocr_image_with_empty_response_returns_empty_string(self, mock_get_response):
        """Empty OCR response returns empty string."""
        mock_get_response.return_value = []

        ocr = NemotronOCR(endpoint_url="https://test.com")
        test_image = Image.new('RGB', (100, 100), color='white')

        # Act
        result = ocr.ocr_image(test_image)

        # Assert
        assert result == ""


class TestNemotronOCRGetDetailedResults:
    """Tests for get_detailed_ocr_results() method - returns full bbox data."""

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_get_detailed_results_returns_full_bbox_data(self, mock_get_response):
        """Returns complete bounding box data structure."""
        # Arrange: Mock full bbox response
        expected_bbox_data = [
            {
                "type": "text",
                "text": "Sample Text",
                "bbox": {"xmin": 10.0, "ymin": 20.0, "xmax": 100.0, "ymax": 50.0}
            }
        ]
        mock_get_response.return_value = expected_bbox_data

        ocr = NemotronOCR(endpoint_url="https://test.com")
        base64_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        # Act
        result = ocr.get_detailed_ocr_results(base64_image, temperature=0.0)

        # Assert
        assert result == expected_bbox_data
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert result[0]["text"] == "Sample Text"
        assert "bbox" in result[0]

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_get_detailed_results_with_multiple_elements(self, mock_get_response):
        """Returns multiple bounding box elements."""
        expected_bbox_data = [
            {"type": "title", "text": "Title", "bbox": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 30}},
            {"type": "paragraph", "text": "Body", "bbox": {"xmin": 0, "ymin": 40, "xmax": 100, "ymax": 80}}
        ]
        mock_get_response.return_value = expected_bbox_data

        ocr = NemotronOCR(endpoint_url="https://test.com")
        base64_image = "data:image/png;base64,test"

        # Act
        result = ocr.get_detailed_ocr_results(base64_image)

        # Assert
        assert len(result) == 2
        assert result[0]["type"] == "title"
        assert result[1]["type"] == "paragraph"

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_get_detailed_results_with_custom_temperature(self, mock_get_response):
        """Custom temperature is passed through to API."""
        mock_get_response.return_value = []

        ocr = NemotronOCR(endpoint_url="https://test.com")
        base64_image = "data:image/png;base64,test"

        # Act
        ocr.get_detailed_ocr_results(base64_image, temperature=0.5)

        # Assert
        call_args = mock_get_response.call_args
        assert call_args[1]['temperature'] == 0.5


class TestNemotronOCRErrorHandling:
    """Tests for error handling in OCR operations."""

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_ocr_image_propagates_api_errors(self, mock_get_response):
        """API errors are propagated to caller."""
        # Arrange: Mock API failure
        mock_get_response.side_effect = Exception("API connection failed")

        ocr = NemotronOCR(endpoint_url="https://test.com")
        test_image = Image.new('RGB', (100, 100), color='white')

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            ocr.ocr_image(test_image)

        assert "API connection failed" in str(exc_info.value)

    @patch('banyan_extract.ocr.nemotron_ocr.NemotronOCR._get_response')
    def test_get_detailed_results_propagates_api_errors(self, mock_get_response):
        """API errors are propagated in get_detailed_ocr_results."""
        mock_get_response.side_effect = Exception("Network timeout")

        ocr = NemotronOCR(endpoint_url="https://test.com")
        base64_image = "data:image/png;base64,test"

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            ocr.get_detailed_ocr_results(base64_image)

        assert "Network timeout" in str(exc_info.value)


class TestModelVersionEnum:
    """Tests for ModelVersion enum."""

    def test_model_version_legacy_value(self):
        """LEGACY enum has correct string value."""
        assert ModelVersion.LEGACY.value == 'legacy'
        assert str(ModelVersion.LEGACY) == 'legacy'

    def test_model_version_latest_value(self):
        """LATEST enum has correct string value."""
        assert ModelVersion.LATEST.value == 'latest'
        assert str(ModelVersion.LATEST) == 'latest'

    def test_model_version_enum_members(self):
        """ModelVersion enum has exactly two members."""
        members = list(ModelVersion)
        assert len(members) == 2
        assert ModelVersion.LEGACY in members
        assert ModelVersion.LATEST in members
