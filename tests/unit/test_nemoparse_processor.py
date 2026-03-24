"""
Unit tests for NemoparseProcessor class.

These tests verify the functionality of the NemoparseProcessor class
using mocking for external dependencies like the Nemotron OCR API.

Test Organization:
- Initialization tests: Test constructor and setup
- Core functionality tests: Test main processing methods
- Error handling tests: Test robust error handling
- Input validation tests: Test input parameter validation
- Edge case tests: Test boundary conditions and unusual scenarios
- Integration tests: Test multi-component interactions
"""

import os
import sys
import io
import tempfile
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.abspath('/projects/src'))

from banyan_extract.processor.nemoparse_processor import NemoparseProcessor
from banyan_extract.output.nemoparse_output import NemoparseData


class TestNemoparseProcessorInitialization:
    """Tests for NemoparseProcessor initialization."""

    def test_initialization_with_default_parameters(self):
        """Test that NemoparseProcessor initializes with default parameters."""
        processor = NemoparseProcessor()
        
        assert processor.nemotron_ocr is not None
        assert processor.nemotron_ocr.model_url == ""
        assert processor.nemotron_ocr.model == "nvidia/nemoretriever-parse"
        assert processor.sort_by_position == True

    def test_initialization_with_custom_parameters(self):
        """Test that NemoparseProcessor initializes with custom parameters."""
        custom_endpoint = "http://custom-endpoint:8000/v1"
        custom_model = "custom/nemoparse-model"
        custom_sort = False
        
        processor = NemoparseProcessor(
            endpoint_url=custom_endpoint,
            model_name=custom_model,
            sort_by_position=custom_sort
        )
        
        assert processor.nemotron_ocr.model_url == custom_endpoint
        assert processor.nemotron_ocr.model == custom_model
        assert processor.sort_by_position == custom_sort


class TestNemoparseProcessorSorting:
    """Tests for the sort_elements_by_position method."""

    def test_sort_elements_by_position_functionality(self):
        """Test that elements are sorted correctly by spatial position."""
        processor = NemoparseProcessor()
        
        # Sample bbox data with different positions
        bbox_data = [
            {
                'type': 'Text',
                'bbox': {'xmin': 0.5, 'ymin': 0.5, 'xmax': 0.8, 'ymax': 0.6},
                'text': 'Bottom text'
            },
            {
                'type': 'Section-header',
                'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.9, 'ymax': 0.2},
                'text': 'Top header'
            },
            {
                'type': 'Text',
                'bbox': {'xmin': 0.2, 'ymin': 0.3, 'xmax': 0.7, 'ymax': 0.4},
                'text': 'Middle text'
            }
        ]
        
        width, height = 1000, 1000
        sorted_elements = processor.sort_elements_by_position(bbox_data, width, height)
        
        # Verify sorting order (should be: header, middle text, bottom text)
        assert sorted_elements[0]['text'] == 'Top header'
        assert sorted_elements[1]['text'] == 'Middle text'
        assert sorted_elements[2]['text'] == 'Bottom text'
        
        # Verify type priority (headers should come before text at same position)
        same_position_elements = [
            {
                'type': 'Text',
                'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2},
                'text': 'Text element'
            },
            {
                'type': 'Section-header',
                'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2},
                'text': 'Header element'
            }
        ]
        
        sorted_same_pos = processor.sort_elements_by_position(same_position_elements, width, height)
        assert sorted_same_pos[0]['type'] == 'Section-header'
        assert sorted_same_pos[1]['type'] == 'Text'


class TestNemoparseProcessorImageProcessing:
    """Tests for image processing methods."""

    def test_encode_image_success(self):
        """Test successful image encoding."""
        processor = NemoparseProcessor()
        
        # Create a test image
        test_image = b'sample_image_data'
        
        # Mock base64 encoding
        with patch('base64.b64encode') as mock_encode:
            mock_encode.return_value = b'encoded_data'
            
            result = processor._encode_image(test_image)
            
            assert result == 'encoded_data'
            mock_encode.assert_called_once_with(test_image)

    def test_encode_image_failure(self):
        """Test image encoding failure handling."""
        processor = NemoparseProcessor()
        
        # Create a test image that will cause an error
        test_image = b'problematic_image_data'
        
        # Mock base64 encoding to raise an exception
        with patch('base64.b64encode') as mock_encode:
            mock_encode.side_effect = Exception("Encoding error")
            
            result = processor._encode_image(test_image)
            
            assert result is None


class TestNemoparseProcessorDocumentProcessing:
    """Tests for document processing methods."""

    def test_process_document_success_with_mocked_api(self):
        """Test successful document processing with mocked API responses."""
        processor = NemoparseProcessor()
        
        # Create a mock image
        mock_image = Image.new('RGB', (100, 100), color='white')
        
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        mock_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        # Mock the OCR API response
        mock_bbox_data = [
            {
                'type': 'Section-header',
                'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.9, 'ymax': 0.2},
                'text': 'Test Header'
            },
            {
                'type': 'Text',
                'bbox': {'xmin': 0.1, 'ymin': 0.3, 'xmax': 0.8, 'ymax': 0.4},
                'text': 'Test paragraph text'
            }
        ]
        
        # Mock the nemotron_ocr.get_detailed_ocr_results method using MagicMock
        processor.nemotron_ocr.get_detailed_ocr_results = MagicMock(return_value=mock_bbox_data)
        
        # Mock the get_pages method to return our test image using MagicMock
        processor.get_pages = MagicMock(return_value=[image_bytes])
        
        # Process the document
        result = processor.process_document("test.pdf")
        
        # Verify the result
        assert result is not None
        assert len(result.text) == 1
        assert len(result.bboxdata) == 1
        
        # Check that the text was processed correctly
        assert any('Test Header' in text for text in result.text[0])
        assert any('Test paragraph text' in text for text in result.text[0])
        
        # Verify that the mocked methods were called correctly
        processor.nemotron_ocr.get_detailed_ocr_results.assert_called_once()
        processor.get_pages.assert_called_once_with("test.pdf")

    def test_process_document_api_failure(self):
        """Test document processing when API fails."""
        processor = NemoparseProcessor()
        
        # Create a mock image
        mock_image = Image.new('RGB', (100, 100), color='white')
        
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        mock_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        # Mock the OCR API to return empty results (simulating failure)
        processor.nemotron_ocr.get_detailed_ocr_results = Mock(return_value=[])
        
        # Mock the get_pages method to return our test image
        processor.get_pages = Mock(return_value=[image_bytes])
        
        # Process the document
        result = processor.process_document("test.pdf")
        
        # Verify the result (should have empty data but not crash)
        assert result is not None
        assert len(result.text) == 1
        assert len(result.text[0]) == 0  # Empty text due to API failure

    def test_process_page_success(self):
        """Test successful page processing."""
        processor = NemoparseProcessor()
        
        # Create a mock image
        mock_image = Image.new('RGB', (100, 100), color='white')
        
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        mock_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        # Mock the OCR API response
        mock_bbox_data = [
            {
                'type': 'Text',
                'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2},
                'text': 'Single page text'
            }
        ]
        
        # Mock the nemotron_ocr.get_detailed_ocr_results method using MagicMock
        processor.nemotron_ocr.get_detailed_ocr_results = MagicMock(return_value=mock_bbox_data)
        
        # Process the page
        result = processor.process_page(image_bytes)
        
        # Verify the result
        assert result is not None
        assert isinstance(result, NemoparseData)
        assert len(result.text) == 1
        assert 'Single page text' in result.text[0]
        
        # Verify that the mocked method was called correctly
        processor.nemotron_ocr.get_detailed_ocr_results.assert_called_once()


class TestNemoparseProcessorErrorHandling:
    """Error handling tests for NemoparseProcessor."""

    def test_network_error_handling(self):
        """Test handling of network errors during API calls."""
        processor = NemoparseProcessor()
        
        # Create a mock image
        mock_image = Image.new('RGB', (100, 100), color='white')
        
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        mock_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        # Mock the OCR API to raise a network error
        processor.nemotron_ocr.get_detailed_ocr_results = Mock(side_effect=Exception("Network error: Connection failed"))
        
        # Process the page - should raise the exception (current behavior)
        with pytest.raises(Exception) as exc_info:
            processor.process_page(image_bytes)
        
        assert "Network error: Connection failed" in str(exc_info.value)

    def test_timeout_error_handling(self):
        """Test handling of timeout errors during API calls."""
        processor = NemoparseProcessor()
        
        # Create a mock image
        mock_image = Image.new('RGB', (100, 100), color='white')
        
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        mock_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        # Mock the OCR API to raise a timeout error
        processor.nemotron_ocr.get_detailed_ocr_results = Mock(side_effect=TimeoutError("Request timed out"))
        
        # Process the page - should raise the timeout error (current behavior)
        with pytest.raises(TimeoutError) as exc_info:
            processor.process_page(image_bytes)
        
        assert "Request timed out" in str(exc_info.value)

    def test_batch_processing_error_handling(self):
        """Test handling of errors during batch processing."""
        processor = NemoparseProcessor()
        
        # Create mock images
        mock_image1 = Image.new('RGB', (100, 100), color='white')
        mock_image2 = Image.new('RGB', (100, 100), color='lightgray')
        
        # Convert images to bytes
        img_byte_arr1 = io.BytesIO()
        mock_image1.save(img_byte_arr1, format='PNG')
        image_bytes1 = img_byte_arr1.getvalue()
        
        img_byte_arr2 = io.BytesIO()
        mock_image2.save(img_byte_arr2, format='PNG')
        image_bytes2 = img_byte_arr2.getvalue()
        
        # Mock the OCR API to succeed for first doc but fail for second
        def mock_ocr_response(base64_image):
            if 'doc1' in base64_image:
                return [
                    {
                        'type': 'Text',
                        'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2},
                        'text': 'Document 1 text'
                    }
                ]
            else:
                raise Exception("API error for document 2")
        
        processor.nemotron_ocr.get_detailed_ocr_results = Mock(side_effect=mock_ocr_response)
        
        # Mock the get_pages method
        def mock_get_pages(filepath):
            if 'doc1' in filepath:
                return [image_bytes1]
            elif 'doc2' in filepath:
                return [image_bytes2]
            return []
        
        processor.get_pages = Mock(side_effect=mock_get_pages)
        
        # Process batch documents - should fail on second document
        filepaths = ['doc1.pdf', 'doc2.pdf']
        
        # Should raise exception for the second document
        with pytest.raises(Exception) as exc_info:
            processor.process_batch_documents(filepaths, use_checkpointing=False)
        
        assert "API error for document 2" in str(exc_info.value)


class TestNemoparseProcessorEdgeCases:
    """Edge case tests for NemoparseProcessor."""

    def test_handle_empty_document(self):
        """Test handling of empty document (no pages)."""
        processor = NemoparseProcessor()
        
        # Mock get_pages to return empty list
        processor.get_pages = Mock(return_value=[])
        
        # Process the document
        result = processor.process_document("empty.pdf")
        
        # Verify the result (should have empty data but not crash)
        assert result is not None
        assert len(result.text) == 0
        assert len(result.bboxdata) == 0

    def test_process_document_with_sorting_disabled(self):
        """Test document processing with sorting disabled."""
        processor = NemoparseProcessor(sort_by_position=False)
        
        # Create a mock image
        mock_image = Image.new('RGB', (100, 100), color='white')
        
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        mock_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        # Mock the OCR API response with unsorted data
        mock_bbox_data = [
            {
                'type': 'Text',
                'bbox': {'xmin': 0.5, 'ymin': 0.5, 'xmax': 0.8, 'ymax': 0.6},
                'text': 'Bottom text'
            },
            {
                'type': 'Section-header',
                'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.9, 'ymax': 0.2},
                'text': 'Top header'
            }
        ]
        
        # Mock the nemotron_ocr.get_detailed_ocr_results method
        processor.nemotron_ocr.get_detailed_ocr_results = Mock(return_value=mock_bbox_data)
        
        # Mock the get_pages method to return our test image
        processor.get_pages = Mock(return_value=[image_bytes])
        
        # Process the document
        result = processor.process_document("test.pdf")
        
        # Verify the result (should preserve original order when sorting is disabled)
        assert result is not None
        assert len(result.text) == 1
        
        # When sorting is disabled, the order should match the original bbox_data
        text_content = result.text[0]
        assert text_content[0] == 'Bottom text'  # First in original data
        assert text_content[1] == '# Top header'   # Second in original data (with # prefix)

    def test_process_document_with_special_characters(self):
        """Test document processing with special characters in text."""
        processor = NemoparseProcessor()
        
        # Create a mock image
        mock_image = Image.new('RGB', (100, 100), color='white')
        
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        mock_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        # Mock the OCR API response with special characters
        mock_bbox_data = [
            {
                'type': 'Text',
                'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.8, 'ymax': 0.2},
                'text': 'Text with special chars: ©®™&<>'
            }
        ]
        
        # Mock the nemotron_ocr.get_detailed_ocr_results method
        processor.nemotron_ocr.get_detailed_ocr_results = Mock(return_value=mock_bbox_data)
        
        # Mock the get_pages method to return our test image
        processor.get_pages = Mock(return_value=[image_bytes])
        
        # Process the document
        result = processor.process_document("test.pdf")
        
        # Verify the result preserves special characters
        assert result is not None
        assert len(result.text) == 1
        assert 'Text with special chars: ©®™&<>' in result.text[0]


class TestNemoparseProcessorInputValidation:
    """Input validation tests for NemoparseProcessor."""

    def test_process_document_with_invalid_filepath(self):
        """Test handling of invalid file paths."""
        processor = NemoparseProcessor()
        
        # Test with None filepath
        with pytest.raises(Exception):
            processor.process_document(None)
        
        # Test with empty string filepath
        with pytest.raises(Exception):
            processor.process_document("")
        
        # Test with non-existent file
        with pytest.raises(Exception):
            processor.process_document("/non/existent/file.pdf")

    def test_process_page_with_invalid_image(self):
        """Test handling of invalid image data."""
        processor = NemoparseProcessor()
        
        # Test with None image data - should raise exception
        with pytest.raises(Exception):
            processor.process_page(None)
        
        # Test with empty bytes - should raise exception
        with pytest.raises(Exception):
            processor.process_page(b"")
        
        # Test with invalid image bytes - should raise exception
        with pytest.raises(Exception):
            processor.process_page(b"invalid_image_data")

    def test_process_batch_with_empty_list(self):
        """Test handling of empty file list in batch processing."""
        processor = NemoparseProcessor()
        
        # Test with empty list
        results = processor.process_batch_documents([], use_checkpointing=False)
        assert len(results) == 0
        
        # Test with None - should raise exception
        with pytest.raises(TypeError):
            processor.process_batch_documents(None, use_checkpointing=False)

    def test_process_batch_with_invalid_filepaths(self):
        """Test handling of invalid file paths in batch processing."""
        processor = NemoparseProcessor()
        
        # Test with list containing None and invalid paths
        filepaths = [None, "", "/non/existent/file.pdf"]
        
        # Mock get_pages to handle the invalid paths gracefully
        def mock_get_pages(filepath):
            if filepath is None or filepath == "" or not os.path.exists(filepath):
                return []
            return [b"mock_image_data"]
        
        processor.get_pages = Mock(side_effect=mock_get_pages)
        
        # Process batch - should handle invalid paths gracefully
        results = processor.process_batch_documents(filepaths, use_checkpointing=False)
        
        # Should return results for all filepaths (even if empty)
        assert len(results) == len(filepaths)
        assert all(result is not None for result in results)


class TestNemoparseProcessorFileHandling:
    """Tests for file handling methods."""

    def test_get_pages_with_png_file(self):
        """Test get_pages method with PNG file."""
        processor = NemoparseProcessor()
        
        # Create a temporary PNG file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            # Create a simple PNG image
            img = Image.new('RGB', (100, 100), color='white')
            img.save(tmp_file, format='PNG')
            tmp_file_path = tmp_file.name
        
        try:
            # Test get_pages with PNG file
            pages = processor.get_pages(tmp_file_path)
            
            # Verify we get one page
            assert len(pages) == 1
            assert isinstance(pages[0], bytes)
            
        finally:
            # Clean up
            os.unlink(tmp_file_path)

    def test_get_pages_with_unsupported_file(self):
        """Test get_pages method with unsupported file type."""
        processor = NemoparseProcessor()
        
        # Create a temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix='.unsupported', delete=False) as tmp_file:
            tmp_file.write(b'test content')
            tmp_file_path = tmp_file.name
        
        try:
            # Test get_pages with unsupported file - should raise exception
            with pytest.raises(Exception) as exc_info:
                processor.get_pages(tmp_file_path)
            
            assert "Unsupported filetype" in str(exc_info.value)
            
        finally:
            # Clean up
            os.unlink(tmp_file_path)


class TestNemoparseProcessorIntegration:
    """Integration tests for NemoparseProcessor."""

    def test_process_batch_documents(self):
        """Test batch document processing."""
        processor = NemoparseProcessor()
        
        # Create mock images
        mock_image1 = Image.new('RGB', (100, 100), color='white')
        mock_image2 = Image.new('RGB', (100, 100), color='lightgray')
        
        # Convert images to bytes
        img_byte_arr1 = io.BytesIO()
        mock_image1.save(img_byte_arr1, format='PNG')
        image_bytes1 = img_byte_arr1.getvalue()
        
        img_byte_arr2 = io.BytesIO()
        mock_image2.save(img_byte_arr2, format='PNG')
        image_bytes2 = img_byte_arr2.getvalue()
        
        # Mock the OCR API response
        mock_bbox_data = [
            {
                'type': 'Text',
                'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2},
                'text': 'Document 1 text'
            }
        ]
        
        # Mock the nemotron_ocr.get_detailed_ocr_results method
        processor.nemotron_ocr.get_detailed_ocr_results = Mock(return_value=mock_bbox_data)
        
        # Mock the get_pages method
        def mock_get_pages(filepath):
            if 'doc1' in filepath:
                return [image_bytes1]
            elif 'doc2' in filepath:
                return [image_bytes2]
            return []
        
        processor.get_pages = Mock(side_effect=mock_get_pages)
        
        # Process batch documents
        filepaths = ['doc1.pdf', 'doc2.pdf']
        results = processor.process_batch_documents(filepaths, use_checkpointing=False)
        
        # Verify we got results for both documents
        assert len(results) == 2
        assert all(result is not None for result in results)

    def test_process_document_with_multiple_pages(self):
        """Test document processing with multiple pages."""
        processor = NemoparseProcessor()
        
        # Create mock images for multiple pages
        mock_images = []
        colors = ['white', 'lightgray', 'gray']
        for i in range(3):
            img = Image.new('RGB', (100, 100), color=colors[i])
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            mock_images.append(img_byte_arr.getvalue())
        
        # Mock the OCR API response
        def mock_ocr_response(base64_image):
            page_num = len(mock_ocr_responses) + 1
            mock_ocr_responses.append(page_num)
            return [
                {
                    'type': 'Text',
                    'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2},
                    'text': f'Page {page_num} text'
                }
            ]
        
        mock_ocr_responses = []
        
        # Mock the nemotron_ocr.get_detailed_ocr_results method
        processor.nemotron_ocr.get_detailed_ocr_results = Mock(side_effect=mock_ocr_response)
        
        # Mock the get_pages method to return multiple pages
        processor.get_pages = Mock(return_value=mock_images)
        
        # Process the document
        result = processor.process_document("multi_page.pdf")
        
        # Verify we got results for all pages
        assert result is not None
        assert len(result.text) == 3  # One entry per page
        
        # Verify each page's text is present
        for i, page_text in enumerate(result.text):
            assert f'Page {i+1} text' in page_text[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
