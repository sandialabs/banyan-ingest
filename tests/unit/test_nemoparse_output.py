"""
Unit tests for NemoparseOutput class.

These tests verify the functionality of the NemoparseOutput class
without mocking, using real implementations wherever possible.
"""

import os
import tempfile
import json
from pathlib import Path
from PIL import Image

import pytest

import sys
import os
sys.path.insert(0, os.path.abspath('/projects/src'))

from banyan_extract.output.nemoparse_output import NemoparseOutput, NemoparseData


class TestNemoparseOutputUnit:
    """Unit tests for NemoparseOutput class methods."""

    def test_initialization(self):
        """Test that NemoparseOutput initializes with empty lists."""
        output = NemoparseOutput()
        
        assert output.text == []
        assert output.images == []
        assert output.tables == []
        assert output.bboxdata == []
        assert output.bbox_image == []

    def test_add_output(self):
        """Test adding output data to the NemoparseOutput instance."""
        output = NemoparseOutput()
        
        # Create sample data
        sample_data = NemoparseData(
            text=["Sample text"],
            bbox_json=[{"element": "text", "bbox": [0, 0, 100, 20]}],
            images=[],
            tables=[],
            bbox_image=Image.new('RGB', (100, 100), color='white')
        )
        
        # Add the data
        output.add_output(sample_data)
        
        # Verify the data was added
        assert len(output.text) == 1
        assert len(output.bboxdata) == 1
        assert len(output.bbox_image) == 1
        assert output.text[0] == ["Sample text"]

    def test_get_bbox_output_with_data(self):
        """Test getting bbox output with bbox data included."""
        output = NemoparseOutput()
        
        # Add sample bbox data
        sample_bbox_data = [
            [{"element": "text", "bbox": [0, 0, 100, 20], "content": "Hello"}],
            [{"element": "image", "bbox": [50, 50, 150, 100]}]
        ]
        output.bboxdata = sample_bbox_data
        
        result = output.get_bbox_output(with_bbox_data=True)
        
        # Verify the result contains bbox data
        assert "page_0" in result
        assert "page_1" in result
        assert result["page_0"][0]["bbox"] == [0, 0, 100, 20]

    def test_get_bbox_output_without_data(self):
        """Test getting bbox output without bbox data."""
        output = NemoparseOutput()
        
        # Add sample bbox data
        sample_bbox_data = [
            [{"element": "text", "bbox": [0, 0, 100, 20], "content": "Hello"}],
            [{"element": "image", "bbox": [50, 50, 150, 100]}]
        ]
        output.bboxdata = sample_bbox_data
        
        result = output.get_bbox_output(with_bbox_data=False)
        
        # Verify bbox data is excluded
        assert "page_0" in result
        assert "page_1" in result
        assert "bbox" not in result["page_0"][0]
        assert "content" in result["page_0"][0]

    def test_get_output_as_markdown(self):
        """Test getting output as markdown format."""
        output = NemoparseOutput()
        
        # Add sample text data
        output.text = [
            ["# Heading", "Paragraph text"],
            ["More text"]
        ]
        
        result = output.get_output_as_markdown()
        
        # Verify markdown formatting
        assert "# Heading" in result
        assert "Paragraph text" in result
        assert "More text" in result

    def test_get_content_list(self):
        """Test getting content as a list."""
        output = NemoparseOutput()
        
        # Add sample text data
        output.text = [
            ["First page text"],
            ["Second page text"]
        ]
        
        result = output.get_content_list()
        
        # Verify content list structure
        assert len(result) == 2
        assert result[0] == "First page text"
        assert result[1] == "Second page text"

    def test_get_images(self):
        """Test getting images from output."""
        output = NemoparseOutput()
        
        # Create sample images
        img1 = Image.new('RGB', (100, 100), color='white')
        img2 = Image.new('RGB', (200, 150), color='gray')
        
        output.images = [[img1], [img2]]
        
        result = output.get_images()
        
        # Verify images are returned
        assert len(result) == 2
        assert result[0] == img1
        assert result[1] == img2


class TestNemoparseOutputEdgeCases:
    """Edge case tests for NemoparseOutput."""

    def test_empty_output(self):
        """Test behavior with empty output."""
        output = NemoparseOutput()
        
        # Test methods with empty data
        assert output.get_bbox_output() == {}
        assert output.get_output_as_markdown() == ""
        assert output.get_content_list() == []
        assert output.get_images() == []

    def test_multiple_pages(self):
        """Test handling of multiple pages of data."""
        output = NemoparseOutput()
        
        # Add data for multiple pages
        for i in range(5):
            sample_data = NemoparseData(
                text=[f"Page {i} text"],
                bbox_json=[{"page": i, "element": "text"}],
                images=[],
                tables=[],
                bbox_image=Image.new('RGB', (100, 100), color='white')
            )
            output.add_output(sample_data)
        
        # Verify all pages are stored
        assert len(output.text) == 5
        assert len(output.bboxdata) == 5
        assert len(output.bbox_image) == 5