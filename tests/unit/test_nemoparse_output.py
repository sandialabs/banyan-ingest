"""
Unit tests for NemoparseOutput class.

These tests verify the functionality of the NemoparseOutput class
without mocking, using real implementations wherever possible.

Dependency Requirements: nemotronparse dependencies (openai) for full testing
"""

import os
import json
from pathlib import Path
from PIL import Image

import pytest

NemoparseOutput = pytest.importorskip("banyan_extract.output.nemoparse_output").NemoparseOutput
NemoparseData = pytest.importorskip("banyan_extract.output.nemoparse_output").NemoparseData


@pytest.mark.requires_nemotronparse
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
            bbox_image=Image.new('RGB', (100, 100), color='white'),
            page_number=1,
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


@pytest.mark.requires_nemotronparse
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
                bbox_image=Image.new('RGB', (100, 100), color='white'),
                page_number=i+1,
            )
            output.add_output(sample_data)
        
        # Verify all pages are stored
        assert len(output.text) == 5
        assert len(output.bboxdata) == 5
        assert len(output.bbox_image) == 5


def _two_page_output():
    bbox = {"xmin": 0.0918, "ymin": 0.0383, "xmax": 0.8965, "ymax": 0.0523}
    output = NemoparseOutput()
    output.add_output(NemoparseData(
        text=["Page one content goes here", "Here is some more *text*"],
        bbox_json=[{"type": "Text", "text": "Page 1 text", "bbox": bbox}],
        images=[], tables=[],
        bbox_image=Image.new('RGB', (10, 10), color='white'),
        page_number=1,
    ))
    output.add_output(NemoparseData(
        text=["Here is the second page."],
        bbox_json=[{"type": "Text", "text": "Page 2 text", "bbox": bbox}],
        images=[], tables=[],
        bbox_image=Image.new('RGB', (10, 10), color='white'),
        page_number=2,
    ))
    return output


EXPECTED_PAGED_MARKDOWN = (
    "[//]: # <PAGE 1>\n\n"
    "Page one content goes here\n\n"
    "Here is some more *text*\n\n"
    "[//]: # <PAGE 2>\n\n"
    "Here is the second page.\n"
)


@pytest.mark.requires_nemotronparse
class TestNemoparseOutputPageFormat:
    """Verify page-separated markdown and page-grouped bbox output."""

    def test_markdown_has_page_headers(self, tmp_path):
        output = _two_page_output()
        output.save_output(str(tmp_path), "doc")
        assert (tmp_path / "doc.md").read_text() == EXPECTED_PAGED_MARKDOWN

    def test_return_bytes_markdown_matches_saved(self, tmp_path):
        output = _two_page_output()
        result = output.return_bytes(str(tmp_path), "doc")
        assert result["markdown"].decode("utf-8") == EXPECTED_PAGED_MARKDOWN

    def test_get_output_as_markdown_has_page_headers(self):
        assert _two_page_output().get_output_as_markdown() == EXPECTED_PAGED_MARKDOWN

    def test_bbox_json_grouped_by_page(self, tmp_path):
        output = _two_page_output()
        output.save_output(str(tmp_path), "doc", save_bbox_data=True)
        data = json.loads((tmp_path / "doc_bbox.json").read_text())
        assert [page["page"] for page in data] == [1, 2]
        assert data[0]["content"][0]["text"] == "Page 1 text"
        assert data[1]["content"][0]["text"] == "Page 2 text"

    def test_return_bytes_bbox_summary_grouped_by_page(self, tmp_path):
        output = _two_page_output()
        result = output.return_bytes(str(tmp_path), "doc", save_bbox_data=True)
        data = json.loads(result["bbox_summary"].decode("utf-8"))
        assert [page["page"] for page in data] == [1, 2]

    def test_page_number_line_ranges(self, tmp_path):
        output = _two_page_output()
        result = output.return_bytes(str(tmp_path), "doc", save_page_numbers=True)
        lines = result["markdown"].decode("utf-8").split("\n")
        for page_num, (start, _end) in result["page_number_lines"]:
            assert lines[start] == f"[//]: # <PAGE {page_num}>"
        assert result["page_number_lines"] == [(1, (0, 5)), (2, (6, 9))]

    def test_get_output_as_json_without_bbox(self):
        data = json.loads(_two_page_output().get_output_as_json(with_bbox_data=False))
        assert all("bbox" not in entry for page in data for entry in page)
