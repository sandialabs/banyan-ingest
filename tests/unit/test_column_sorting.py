"""
Unit tests for column-aware bbox sorting algorithm.

These tests verify the column detection and sorting functionality
for multi-column document layouts (e.g., scientific papers, newspapers).

Test Organization:
- Basic cases: Empty document, single column
- Multi-column cases: Two columns, three columns
- Edge cases: Wide elements, tight columns, indented text
- Type priority: Elements at same position sorted by type
"""

import pytest

# Import will be added after we create the column detection module
# For now, we'll test through the NemoparseProcessor interface

NemoparseProcessor = pytest.importorskip("banyan_extract.processor.nemoparse_processor").NemoparseProcessor


@pytest.mark.requires_nemotronparse
class TestColumnSortingBasics:
    """Tests for basic column sorting functionality."""

    def setup_method(self):
        """Setup for each test - create processor with column detection enabled."""
        # Note: column_detection_mode parameter doesn't exist yet
        self.processor = NemoparseProcessor()

    def test_empty_document_returns_empty_list(self):
        """Empty document should return empty list."""
        processor = NemoparseProcessor()
        data = []

        result = processor.sort_elements_by_position(data, width=1000, height=1000)

        assert result == []
        assert len(result) == 0

    def test_single_column_sorts_by_y_position(self):
        """Elements in one column should sort by y-position (top to bottom)."""
        data = [
            {'bbox': {'xmin': 0.1, 'ymin': 0.3, 'xmax': 0.4, 'ymax': 0.35}, 'type': 'Text', 'text': 'C'},
            {'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.4, 'ymax': 0.15}, 'type': 'Text', 'text': 'A'},
            {'bbox': {'xmin': 0.1, 'ymin': 0.2, 'xmax': 0.4, 'ymax': 0.25}, 'type': 'Text', 'text': 'B'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        assert texts == ['A', 'B', 'C']  # Sorted by y-position top to bottom


@pytest.mark.requires_nemotronparse
class TestTwoColumnSorting:
    """Tests for two-column document layout."""

    def setup_method(self):
        """Setup for each test."""
        self.processor = NemoparseProcessor()

    def test_two_columns_reads_left_then_right(self):
        """
        Two-column document should read left column completely, then right column.

        This is the core test for column-aware sorting. With the current implementation,
        this will FAIL because it sorts by (x, y), reading left-right at each y-level.
        """
        data = [
            {'bbox': {'xmin': 0.05, 'ymin': 0.1, 'xmax': 0.45, 'ymax': 0.15}, 'type': 'Text', 'text': 'L1'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Text', 'text': 'R1'},
            {'bbox': {'xmin': 0.05, 'ymin': 0.3, 'xmax': 0.45, 'ymax': 0.35}, 'type': 'Text', 'text': 'L2'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.3, 'xmax': 0.95, 'ymax': 0.35}, 'type': 'Text', 'text': 'R2'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Should read: left column top-to-bottom, then right column top-to-bottom
        assert texts == ['L1', 'L2', 'R1', 'R2'], f"Expected ['L1', 'L2', 'R1', 'R2'], got {texts}"

    def test_two_columns_with_ragged_edges(self):
        """
        Two-column document where x-min varies slightly within each column (ragged edges).

        This test FAILS with current (x, y) sorting because it treats slight x-min
        variations as different columns, breaking reading order within a column.

        Current implementation sorts by (x, y):
        - (0.049, 200) comes before (0.05, 100) because 0.049 < 0.05
        - This is WRONG - para at y=100 should come before y=200 in same column!
        """
        data = [
            # Left column with ragged x-min values
            {'bbox': {'xmin': 0.050, 'ymin': 0.1, 'xmax': 0.45, 'ymax': 0.15}, 'type': 'Text', 'text': 'L1'},
            {'bbox': {'xmin': 0.049, 'ymin': 0.2, 'xmax': 0.45, 'ymax': 0.25}, 'type': 'Text', 'text': 'L2'},
            {'bbox': {'xmin': 0.051, 'ymin': 0.3, 'xmax': 0.45, 'ymax': 0.35}, 'type': 'Text', 'text': 'L3'},
            # Right column
            {'bbox': {'xmin': 0.55, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Text', 'text': 'R1'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # With column detection: all left column elements (0.049-0.051) assigned to column 0,
        # sorted by y within column: L1, L2, L3, then R1
        assert texts == ['L1', 'L2', 'L3', 'R1'], f"Expected ['L1', 'L2', 'L3', 'R1'], got {texts}"

    def test_two_columns_with_footer(self):
        """
        Two-column document where x-min varies slightly within each column (ragged edges) and there is a Page Footer element. 
        The Page Footer element should always be at the bottom.
        """
        data = [
            {'bbox': {'xmin': 0.05, 'ymin': 0.1, 'xmax': 0.45, 'ymax': 0.15}, 'type': 'Text', 'text': 'L1'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Text', 'text': 'R1'},
            {'bbox': {'xmin': 0.05, 'ymin': 0.3, 'xmax': 0.45, 'ymax': 0.35}, 'type': 'Text', 'text': 'L2'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.3, 'xmax': 0.95, 'ymax': 0.35}, 'type': 'Text', 'text': 'R2'},
            {'bbox': {'xmin': 0.049, 'ymin': 0.90, 'xmax': 0.45, 'ymax': 0.95}, 'type': 'Page-footer', 'text': 'Page 1'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Footer appears after all columns, not just after its assigned column
        assert texts == ['L1', 'L2', 'R1', 'R2', 'Page 1'], f"Expected ['L1', 'L2', 'R1', 'R2', 'Page 1'], got {texts}"

    def test_two_columns_with_wide_element(self):
        """
        Two-column document with wide element (figure/table) spanning both columns.

        Wide elements are NOT special-cased (except footers). They get assigned to a
        column based on their x-min coordinate and appear at their y-position within
        that column. This is acceptable because wide elements already break linear
        reading order in multi-column documents (figures are placed where they fit
        spatially, not where first referenced).

        Scenario: Full-width figure at y=0.5 in left column (x-min=0.05).
        Figure appears at its y-position within left column output.
        """
        data = [
            # Left column
            {'bbox': {'xmin': 0.05, 'ymin': 0.1, 'xmax': 0.45, 'ymax': 0.15}, 'type': 'Text', 'text': 'L1'},
            {'bbox': {'xmin': 0.05, 'ymin': 0.3, 'xmax': 0.45, 'ymax': 0.35}, 'type': 'Text', 'text': 'L2'},
            # Wide figure spanning both columns (assigned to left based on x-min)
            {'bbox': {'xmin': 0.05, 'ymin': 0.5, 'xmax': 0.95, 'ymax': 0.6}, 'type': 'Picture', 'text': 'Fig1'},
            {'bbox': {'xmin': 0.05, 'ymin': 0.7, 'xmax': 0.45, 'ymax': 0.75}, 'type': 'Text', 'text': 'L3'},
            # Right column
            {'bbox': {'xmin': 0.55, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Text', 'text': 'R1'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.3, 'xmax': 0.95, 'ymax': 0.35}, 'type': 'Text', 'text': 'R2'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Figure assigned to left column (x-min=0.05), appears at y=0.5 within that column
        # Reading order: left column (L1, L2, Fig1, L3), then right column (R1, R2)
        assert texts == ['L1', 'L2', 'Fig1', 'L3', 'R1', 'R2'], f"Expected ['L1', 'L2', 'Fig1', 'L3', 'R1', 'R2'], got {texts}"


@pytest.mark.requires_nemotronparse
class TestThreeColumnSorting:
    """Tests for three-column document layout (e.g., newspapers)."""

    def setup_method(self):
        """Setup for each test."""
        self.processor = NemoparseProcessor()

    def test_three_columns_reads_left_to_right(self):
        """
        Three-column document should read each column top-to-bottom, left to right.

        This validates that the gap-based column detection generalizes beyond two columns.
        Gap detection should find 2 gaps and create 3 column boundaries.
        """
        data = [
            # Left column
            {'bbox': {'xmin': 0.05, 'ymin': 0.1, 'xmax': 0.28, 'ymax': 0.15}, 'type': 'Text', 'text': 'L1'},
            {'bbox': {'xmin': 0.05, 'ymin': 0.3, 'xmax': 0.28, 'ymax': 0.35}, 'type': 'Text', 'text': 'L2'},
            # Middle column
            {'bbox': {'xmin': 0.37, 'ymin': 0.1, 'xmax': 0.63, 'ymax': 0.15}, 'type': 'Text', 'text': 'M1'},
            {'bbox': {'xmin': 0.37, 'ymin': 0.3, 'xmax': 0.63, 'ymax': 0.35}, 'type': 'Text', 'text': 'M2'},
            # Right column
            {'bbox': {'xmin': 0.72, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Text', 'text': 'R1'},
            {'bbox': {'xmin': 0.72, 'ymin': 0.3, 'xmax': 0.95, 'ymax': 0.35}, 'type': 'Text', 'text': 'R2'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Should read: left column, middle column, right column (all top-to-bottom)
        assert texts == ['L1', 'L2', 'M1', 'M2', 'R1', 'R2'], f"Expected ['L1', 'L2', 'M1', 'M2', 'R1', 'R2'], got {texts}"

    def test_three_columns_with_ragged_edges(self):
        """
        Three-column document with ragged x-min values within each column.

        Validates that gap detection works correctly with 3 columns and ragged edges.
        """
        data = [
            # Left column with ragged edges
            {'bbox': {'xmin': 0.050, 'ymin': 0.1, 'xmax': 0.28, 'ymax': 0.15}, 'type': 'Text', 'text': 'L1'},
            {'bbox': {'xmin': 0.049, 'ymin': 0.3, 'xmax': 0.28, 'ymax': 0.35}, 'type': 'Text', 'text': 'L2'},
            # Middle column with ragged edges
            {'bbox': {'xmin': 0.37, 'ymin': 0.1, 'xmax': 0.63, 'ymax': 0.15}, 'type': 'Text', 'text': 'M1'},
            {'bbox': {'xmin': 0.371, 'ymin': 0.3, 'xmax': 0.63, 'ymax': 0.35}, 'type': 'Text', 'text': 'M2'},
            # Right column with ragged edges
            {'bbox': {'xmin': 0.72, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Text', 'text': 'R1'},
            {'bbox': {'xmin': 0.719, 'ymin': 0.3, 'xmax': 0.95, 'ymax': 0.35}, 'type': 'Text', 'text': 'R2'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Ragged edges within each column should not affect column assignment
        assert texts == ['L1', 'L2', 'M1', 'M2', 'R1', 'R2'], f"Expected ['L1', 'L2', 'M1', 'M2', 'R1', 'R2'], got {texts}"


@pytest.mark.requires_nemotronparse
class TestTypePrioritySorting:
    """Tests for element type priority within columns."""

    def setup_method(self):
        """Setup for each test."""
        self.processor = NemoparseProcessor()

    def test_type_priority_at_same_position(self):
        """
        Elements at the same (x, y) position should sort by type priority.

        Type priority order (lower number = higher priority):
        0: Section-header
        1: Text
        2: Formula
        3: Code
        4: Picture
        5: Table
        6: Caption
        7: Unknown types

        This ensures headers appear before text, text before pictures, etc.
        when elements overlap or are at the exact same position.
        """
        data = [
            # All at same position in single column
            {'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2}, 'type': 'Caption', 'text': 'Figure 1'},
            {'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2}, 'type': 'Text', 'text': 'Body text'},
            {'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2}, 'type': 'Section-header', 'text': 'Introduction'},
            {'bbox': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.2}, 'type': 'Picture', 'text': 'Image'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Should sort by type priority: Section-header (0), Text (1), Picture (4), Caption (6)
        assert texts == ['Introduction', 'Body text', 'Image', 'Figure 1'], \
            f"Expected ['Introduction', 'Body text', 'Image', 'Figure 1'], got {texts}"

    def test_type_priority_within_two_columns(self):
        """
        Type priority should work within each column independently.

        When elements in different columns have same y-position but different types,
        each column sorts by type priority independently.
        """
        data = [
            # Left column - Text and Header at same y
            {'bbox': {'xmin': 0.05, 'ymin': 0.1, 'xmax': 0.45, 'ymax': 0.15}, 'type': 'Text', 'text': 'L-Text'},
            {'bbox': {'xmin': 0.05, 'ymin': 0.1, 'xmax': 0.45, 'ymax': 0.15}, 'type': 'Section-header', 'text': 'L-Header'},
            # Right column - Caption and Picture at same y
            {'bbox': {'xmin': 0.55, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Caption', 'text': 'R-Caption'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Picture', 'text': 'R-Picture'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Left column: Header before Text, Right column: Picture before Caption
        assert texts == ['L-Header', 'L-Text', 'R-Picture', 'R-Caption'], \
            f"Expected ['L-Header', 'L-Text', 'R-Picture', 'R-Caption'], got {texts}"


@pytest.mark.requires_nemotronparse
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def setup_method(self):
        """Setup for each test."""
        self.processor = NemoparseProcessor()

    def test_tight_columns_no_detection(self):
        """
        Columns separated by x-min gap < threshold should be treated as single column.

        Default gap_threshold is 0.15 (15% of page width).
        Gap detection looks at the gap between x-min values (not physical spacing).
        If x-min values are within 0.15 of each other, no column boundary is detected.

        This is a safe fallback for documents with very tight column spacing
        or documents that aren't actually multi-column.
        """
        data = [
            # "Left column" at x-min=0.10
            {'bbox': {'xmin': 0.10, 'ymin': 0.1, 'xmax': 0.40, 'ymax': 0.15}, 'type': 'Text', 'text': 'A'},
            {'bbox': {'xmin': 0.10, 'ymin': 0.3, 'xmax': 0.40, 'ymax': 0.35}, 'type': 'Text', 'text': 'C'},
            # "Right column" at x-min=0.20 (gap of 0.10 = 10% < 15% threshold)
            {'bbox': {'xmin': 0.20, 'ymin': 0.1, 'xmax': 0.50, 'ymax': 0.15}, 'type': 'Text', 'text': 'B'},
            {'bbox': {'xmin': 0.20, 'ymin': 0.3, 'xmax': 0.50, 'ymax': 0.35}, 'type': 'Text', 'text': 'D'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Gap between x-min values is 0.10 (10%) which is < threshold (15%)
        # Should be treated as single column, sorted by (y, x):
        # y=0.1: A (x=0.10), B (x=0.20) → A, B
        # y=0.3: C (x=0.10), D (x=0.20) → C, D
        # Result: A, B, C, D
        assert texts == ['A', 'B', 'C', 'D'], f"Expected ['A', 'B', 'C', 'D'], got {texts}"

    def test_large_gap_column_detection(self):
        """
        Columns separated by gap >= threshold should be detected as separate columns.

        This is the complement of test_tight_columns_no_detection.
        With a 0.20 gap (20% > 15% threshold), columns should be detected.
        """
        data = [
            # Left column at x=0.1
            {'bbox': {'xmin': 0.10, 'ymin': 0.1, 'xmax': 0.35, 'ymax': 0.15}, 'type': 'Text', 'text': 'A'},
            {'bbox': {'xmin': 0.10, 'ymin': 0.3, 'xmax': 0.35, 'ymax': 0.35}, 'type': 'Text', 'text': 'B'},
            # Right column at x=0.55 (0.20 gap = 20% > 15% threshold)
            {'bbox': {'xmin': 0.55, 'ymin': 0.1, 'xmax': 0.80, 'ymax': 0.15}, 'type': 'Text', 'text': 'C'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.3, 'xmax': 0.80, 'ymax': 0.35}, 'type': 'Text', 'text': 'D'},
        ]

        result = self.processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Gap is 0.20 (20%) which is > threshold (15%)
        # Should detect as two columns, read left column then right column
        # Result: A, B (left column), then C, D (right column)
        assert texts == ['A', 'B', 'C', 'D'], f"Expected ['A', 'B', 'C', 'D'], got {texts}"


@pytest.mark.requires_nemotronparse
class TestConfiguration:
    """Tests for configuration parameters."""

    def test_column_detection_mode_none_disables_detection(self):
        """
        column_detection_mode='none' should disable column detection entirely.

        This restores the original sorting behavior: sort by (x, y, type) without
        any column detection or grouping. Useful for single-column documents or
        when column detection causes problems.
        """
        # Create processor with column detection disabled
        processor = NemoparseProcessor(column_detection_mode='none')

        # Two-column layout that would normally be detected
        data = [
            {'bbox': {'xmin': 0.05, 'ymin': 0.1, 'xmax': 0.45, 'ymax': 0.15}, 'type': 'Text', 'text': 'L1'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Text', 'text': 'R1'},
            {'bbox': {'xmin': 0.05, 'ymin': 0.3, 'xmax': 0.45, 'ymax': 0.35}, 'type': 'Text', 'text': 'L2'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.3, 'xmax': 0.95, 'ymax': 0.35}, 'type': 'Text', 'text': 'R2'},
        ]

        result = processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # With detection disabled, should sort by (x, y):
        # x=50: L1 (y=100), L2 (y=300) → L1, L2
        # x=550: R1 (y=100), R2 (y=300) → R1, R2
        # Result: L1, L2, R1, R2 (same as with detection, but for different reason)
        assert texts == ['L1', 'L2', 'R1', 'R2'], f"Expected ['L1', 'L2', 'R1', 'R2'], got {texts}"

    def test_column_detection_mode_auto_enables_detection(self):
        """
        column_detection_mode='auto' (default) enables column detection.

        This is the default behavior with gap-based column detection.
        """
        # Create processor with default (auto mode)
        processor = NemoparseProcessor(column_detection_mode='auto')

        # Two-column layout with ragged edges (would fail without detection)
        data = [
            {'bbox': {'xmin': 0.050, 'ymin': 0.1, 'xmax': 0.45, 'ymax': 0.15}, 'type': 'Text', 'text': 'L1'},
            {'bbox': {'xmin': 0.049, 'ymin': 0.2, 'xmax': 0.45, 'ymax': 0.25}, 'type': 'Text', 'text': 'L2'},
            {'bbox': {'xmin': 0.55, 'ymin': 0.1, 'xmax': 0.95, 'ymax': 0.15}, 'type': 'Text', 'text': 'R1'},
        ]

        result = processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # With detection enabled, ragged edges handled correctly
        assert texts == ['L1', 'L2', 'R1'], f"Expected ['L1', 'L2', 'R1'], got {texts}"

    def test_custom_gap_threshold(self):
        """
        column_gap_threshold parameter allows customizing the gap detection sensitivity.

        Higher threshold = more tolerant (requires larger gap to detect columns)
        Lower threshold = more sensitive (detects columns with smaller gaps)
        """
        # Create processor with custom threshold of 0.25 (25%)
        processor = NemoparseProcessor(column_gap_threshold=0.25)

        # Two "columns" with 0.20 gap (20%)
        # With default threshold (0.15), this would detect as two columns
        # With threshold=0.25, this should be treated as single column
        data = [
            {'bbox': {'xmin': 0.10, 'ymin': 0.1, 'xmax': 0.35, 'ymax': 0.15}, 'type': 'Text', 'text': 'A'},
            {'bbox': {'xmin': 0.30, 'ymin': 0.1, 'xmax': 0.55, 'ymax': 0.15}, 'type': 'Text', 'text': 'B'},
            {'bbox': {'xmin': 0.10, 'ymin': 0.3, 'xmax': 0.35, 'ymax': 0.35}, 'type': 'Text', 'text': 'C'},
            {'bbox': {'xmin': 0.30, 'ymin': 0.3, 'xmax': 0.55, 'ymax': 0.35}, 'type': 'Text', 'text': 'D'},
        ]

        result = processor.sort_elements_by_position(data, width=1000, height=1000)
        texts = [e['text'] for e in result]

        # Gap of 0.20 (between 0.10 and 0.30) is < threshold (0.25)
        # Should treat as single column: A, B (y=0.1), C, D (y=0.3)
        assert texts == ['A', 'B', 'C', 'D'], f"Expected ['A', 'B', 'C', 'D'], got {texts}"

    def test_default_parameters(self):
        """
        Test that default parameters are set correctly.

        Defaults should be:
        - column_detection_mode='auto'
        - column_gap_threshold=0.15
        - sort_by_position=True (existing parameter)
        """
        processor = NemoparseProcessor()

        # Check that default parameters are set
        assert processor.column_detection_mode == 'auto', \
            f"Expected column_detection_mode='auto', got {processor.column_detection_mode}"
        assert processor.column_gap_threshold == 0.15, \
            f"Expected column_gap_threshold=0.15, got {processor.column_gap_threshold}"
        assert processor.sort_by_position == True, \
            f"Expected sort_by_position=True, got {processor.sort_by_position}"
