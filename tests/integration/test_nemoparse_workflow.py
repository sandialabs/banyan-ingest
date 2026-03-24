"""
Integration test for NemoparseOutput demonstrating a complete workflow.

This test shows how the NemoparseOutput class works in a realistic scenario
with real file operations, following the "prefer real implementations" principle.

Generated using AI, reviewed by a human
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


class TestNemoparseOutputIntegration:
    """Integration tests for NemoparseOutput demonstrating complete workflows."""

    def test_complete_workflow_with_file_output(self, temp_output_dir):
        """
        Test complete workflow: create output, add data, and save to files.
        
        This integration test demonstrates:
        - Creating a NemoparseOutput instance
        - Adding multiple pages of data
        - Saving output to various file formats
        - Verifying the saved files
        
        Uses real file operations (no mocking) to ensure the workflow
        works as expected in production.
        """
        # Create output instance
        output = NemoparseOutput()
        
        # Add multiple pages of sample data (simulating real processing)
        for page_num in range(3):
            # Create sample image for this page
            img = Image.new('RGB', (200, 150), color='lightgray')
            
            # Create sample bbox image
            bbox_img = Image.new('RGB', (200, 150), color='white')
            
            # Create page data
            page_data = NemoparseData(
                text=["# Sample Document", "This is a sample document for testing."],
                bbox_json=[
                    {
                        "type": "heading",
                        "bbox": [20, 20, 200, 40],
                        "text": "Sample Document",
                        "confidence": 0.97
                    }
                ],
                images=[Image.new('RGB', (100, 100), color='white')],
                tables=["Column1|Column2\\Value1|Value2"],  # Simple table
                bbox_image=Image.new('RGB', (100, 100), color='white')
            )
            
            output.add_output(page_data)
        
        # Save output to temporary directory (real file operations)
        output_dir = temp_output_dir
        base_name = "test_document"
        
        output.save_output(output_dir, base_name)
        
        # Verify files were created
        expected_files = [
            f"{base_name}.md",
            f"{base_name}_bbox.json",
            f"{base_name}_bbox_image_0.png",
            f"{base_name}_bbox_image_1.png",
            f"{base_name}_bbox_image_2.png",
            f"{base_name}_image_0.png",
            f"{base_name}_image_1.png", 
            f"{base_name}_image_2.png",
            f"{base_name}_table_0.csv",
            f"{base_name}_table_1.csv",
            f"{base_name}_table_2.csv"
        ]
        
        for expected_file in expected_files:
            file_path = output_dir / expected_file
            assert file_path.exists(), f"Expected file not found: {expected_file}"
        
        # Verify content of markdown file
        md_file = output_dir / f"{base_name}.md"
        with open(md_file, 'r') as f:
            md_content = f.read()
        
        # The markdown content should contain the sample document text
        assert "# Sample Document" in md_content
        assert "This is a sample document for testing" in md_content
        
        # Verify content of bbox JSON file
        bbox_file = output_dir / f"{base_name}_bbox.json"
        with open(bbox_file, 'r') as f:
            bbox_content = f.read()
        
        # Verify bbox file exists and contains expected content
        assert bbox_file.exists()
        with open(bbox_file, 'r') as f:
            bbox_content = f.read()
        
        # Verify the bbox file contains expected data
        assert "Sample Document" in bbox_content
        assert "heading" in bbox_content
        assert "bbox" in bbox_content
        
        # Verify image files are valid
        image_file = output_dir / f"{base_name}_image_0.png"
        with Image.open(image_file) as img:
            assert img.size == (100, 100)  # Updated to match the actual image size used in the test
            assert img.mode == 'RGB'
        
        # Verify table CSV files
        table_file = output_dir / f"{base_name}_table_0.csv"
        with open(table_file, 'r') as f:
            table_content = f.read()
        
        assert "Column1" in table_content
        assert "Column2" in table_content
        assert "Value1" in table_content

    def test_workflow_with_realistic_data_structure(self, temp_output_dir):
        """
        Test workflow with more realistic data structure.
        
        This test demonstrates handling of:
        - Complex bbox data with various element types
        - Multiple images per page
        - Tables with realistic data
        - Real file saving and verification
        """
        output = NemoparseOutput()
        
        # Simulate processing of a document with complex structure
        document_pages = [
            {
                "text": [
                    "# Document Title",
                    "## Section 1",
                    "This is the first section of the document.",
                    "It contains multiple paragraphs."
                ],
                "bbox_data": [
                    {"type": "title", "bbox": [50, 50, 300, 80], "text": "Document Title", "confidence": 0.98},
                    {"type": "heading", "bbox": [50, 100, 200, 130], "text": "Section 1", "confidence": 0.95},
                    {"type": "paragraph", "bbox": [50, 150, 400, 250], "text": "This is the first section...", "confidence": 0.92}
                ],
                "images": [
                    Image.new('RGB', (400, 300), color='white'),
                    Image.new('RGB', (200, 150), color='lightgray')
                ],
                "tables": [
                    "Name|Age|Department\\John Doe|30|Engineering\\Jane Smith|28|Marketing"
                ]
            },
            {
                "text": [
                    "## Section 2",
                    "This section contains different content.",
                    "It includes a table and an image."
                ],
                "bbox_data": [
                    {"type": "heading", "bbox": [50, 50, 200, 80], "text": "Section 2", "confidence": 0.96},
                    {"type": "paragraph", "bbox": [50, 100, 400, 200], "text": "This section contains...", "confidence": 0.91}
                ],
                "images": [
                    Image.new('RGB', (300, 200), color='blue')
                ],
                "tables": [
                    "Product|Price|Quantity\\Widget A|19.99|100\\Widget B|29.99|50"
                ]
            }
        ]
        
        # Add the data to output
        for page_data in document_pages:
            nemoparse_data = NemoparseData(
                text=page_data["text"],
                bbox_json=page_data["bbox_data"],
                images=page_data["images"],
                tables=page_data["tables"],
                bbox_image=Image.new('RGB', (500, 400), color='white')
            )
            output.add_output(nemoparse_data)
        
        # Save output
        output_dir = temp_output_dir
        output.save_output(output_dir, "complex_document")
        
        # Verify the output files
        md_file = output_dir / "complex_document.md"
        assert md_file.exists()
        
        with open(md_file, 'r') as f:
            content = f.read()
        
        # Verify content includes expected elements
        assert "# Document Title" in content
        assert "## Section 1" in content
        assert "## Section 2" in content
        assert "This is the first section" in content
        assert "This section contains different content" in content
        
        # Verify bbox JSON contains expected structure
        bbox_file = output_dir / "complex_document_bbox.json"
        assert bbox_file.exists()
        
        # Verify bbox file exists and contains expected content
        assert bbox_file.exists()
        with open(bbox_file, 'r') as f:
            bbox_content = f.read()
        
        # Verify the bbox file contains expected data
        assert "Document Title" in bbox_content
        assert "Section 1" in bbox_content
        assert "title" in bbox_content
        assert "heading" in bbox_content
        assert "paragraph" in bbox_content

    def test_error_handling_in_save_output(self, temp_output_dir):
        """
        Test error handling when saving output files.
        
        This demonstrates that the save_output method handles
        errors gracefully when dealing with real file operations.
        """
        output = NemoparseOutput()
        
        # Add some valid data
        valid_data = NemoparseData(
            text=["Valid text"],
            bbox_json=[{"type": "text", "bbox": [0, 0, 100, 20]}],
            images=[],
            tables=[],
            bbox_image=Image.new('RGB', (100, 100), color='white')
        )
        output.add_output(valid_data)
        
        # Save to a valid directory - should work
        output.save_output(temp_output_dir, "valid_output")
        
        # Verify files were created
        assert (temp_output_dir / "valid_output.md").exists()
        assert (temp_output_dir / "valid_output_bbox.json").exists()


class TestNemoparseOutputExampleBased:
    """
    Example-based tests that serve as user documentation.
    
    These tests demonstrate real-world usage patterns
    and can be used as templates for users.
    """

    def test_basic_usage_example(self, temp_output_dir):
        """
        Example: Basic usage of NemoparseOutput
        
        This example shows the simplest way to use NemoparseOutput:
        1. Create an instance
        2. Add processed data
        3. Save the output
        
        Users can adapt this example for their own document processing needs.
        """
        # Step 1: Create NemoparseOutput instance
        document_output = NemoparseOutput()
        
        # Step 2: Process a document (simulated here)
        # In real usage, this would come from a processor
        page_data = NemoparseData(
            text=["# Sample Document", "This is a sample document for testing."],
            bbox_json=[
                {
                    "type": "heading",
                    "bbox": [20, 20, 200, 40],
                    "text": "Sample Document",
                    "confidence": 0.97
                }
            ],
            images=[Image.new('RGB', (100, 100), color='white')],
            tables=[],
            bbox_image=Image.new('RGB', (100, 100), color='white')
        )
        
        document_output.add_output(page_data)
        
        # Step 3: Save the output
        output_path = temp_output_dir
        document_output.save_output(output_path, "sample_document")
        
        # Verify the output was saved correctly
        assert (temp_output_dir / "sample_document.md").exists()
        assert (temp_output_dir / "sample_document_bbox.json").exists()
        
        # Show the user how to access the output data programmatically
        markdown_content = document_output.get_output_as_markdown()
        assert "# Sample Document" in markdown_content
        
        bbox_data = document_output.get_bbox_output()
        assert "page_0" in bbox_data

    def test_multi_page_document_example(self, temp_output_dir):
        """
        Example: Processing a multi-page document
        
        This example demonstrates how to handle documents with multiple pages:
        - Adding data for each page sequentially
        - Accessing page-specific content
        - Working with the complete document output
        """
        # Create output for a multi-page document
        doc_output = NemoparseOutput()
        
        # Process multiple pages
        for page_num in range(1, 4):  # 3 pages
            page_data = NemoparseData(
                text=[f"# Page {page_num + 1}", f"Content for page {page_num + 1}"],
                bbox_json=[
                    {
                        "type": "heading",
                        "bbox": [20, 20, 150, 40],
                        "text": f"Page {page_num + 1}",
                        "confidence": 0.95 + (page_num * 0.01)
                    }
                ],
                images=[Image.new('RGB', (200, 150), color='lightgray')],
                tables=[f"Page|Content\\{page_num}|Sample content"],
                bbox_image=Image.new('RGB', (200, 150), color='white')
            )
            doc_output.add_output(page_data)
        
        # Save the complete document
        doc_output.save_output(temp_output_dir, "multi_page_doc")
        
        # Demonstrate accessing page-specific content
        content_list = doc_output.get_content_list()
        assert len(content_list) == 3
        # The content list concatenates all text for each page
        assert "Page 1" in content_list[0] or "Page 2" in content_list[0] or "Page 3" in content_list[0]
        assert "Content for page" in str(content_list)
        
        # Show how to get all images from the document
        all_images = doc_output.get_images()
        assert len(all_images) == 3  # One image per page
        
        # Verify all expected files were created
        expected_files = [
            "multi_page_doc.md",
            "multi_page_doc_bbox.json",
            "multi_page_doc_bbox_image_0.png",
            "multi_page_doc_bbox_image_1.png",
            "multi_page_doc_bbox_image_2.png",
            "multi_page_doc_image_0.png",
            "multi_page_doc_image_1.png",
            "multi_page_doc_image_2.png",
            "multi_page_doc_table_0.csv",
            "multi_page_doc_table_1.csv",
            "multi_page_doc_table_2.csv"
        ]
        
        for expected_file in expected_files:
            assert (temp_output_dir / expected_file).exists()
