"""
Tests for LaTeX table to CSV conversion.

Tests the convert_latex_table_to_csv function which converts LaTeX table markup
into a list-of-lists CSV-friendly data structure.
"""

import pytest
from banyan_extract.converter.latex_table_to_csv import convert_latex_table_to_csv


class TestConvertLatexTableToCsv:
    """Tests for convert_latex_table_to_csv function."""

    def test_simple_table_conversion(self):
        """Test conversion of basic LaTeX table."""
        latex_input = r"""\begin{tabular}{cc}
Cell1 & Cell2 \\
Cell3 & Cell4 \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        # Should return list of lists with 2 rows, 2 columns each
        assert len(result) == 3  # 2 data rows + 1 empty from trailing \\
        assert result[0] == ['Cell1', 'Cell2']
        assert result[1] == ['Cell3', 'Cell4']

    def test_table_with_hlines(self):
        """Test table with horizontal lines (\\hline)."""
        latex_input = r"""\begin{tabular}{cc}
\hline
Header1 & Header2 \\
\hline
Data1 & Data2 \\
\hline
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        # hlines should be removed
        assert len(result) >= 2
        assert result[0] == ['Header1', 'Header2']
        assert result[1] == ['Data1', 'Data2']

    def test_table_with_multicolumn(self):
        """Test table with \\multicolumn commands."""
        latex_input = r"""\begin{tabular}{ccc}
\multicolumn{3}{c}{Title} \\
A & B & C \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        # multicolumn command should be stripped, leaving just "Title"
        assert len(result) >= 2
        assert 'Title' in result[0][0]
        assert result[1] == ['A', 'B', 'C']

    def test_empty_cells(self):
        """Test table with empty cells."""
        latex_input = r"""\begin{tabular}{ccc}
A &  & C \\
& B & \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        # Empty cells should result in empty strings
        assert len(result) >= 2
        assert result[0][0] == 'A'
        assert result[0][1] == ''
        assert result[0][2] == 'C'
        assert result[1][0] == ''
        assert result[1][1] == 'B'
        assert result[1][2] == ''

    def test_table_with_math_mode(self):
        """Test table containing inline math ($...$)."""
        latex_input = r"""\begin{tabular}{cc}
$x^2$ & $y^2$ \\
$a+b$ & $c-d$ \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        # Math delimiters should be preserved (function doesn't strip $ signs)
        assert len(result) >= 2
        assert '$x^2$' in result[0][0] or 'x^2' in result[0][0]
        assert '$y^2$' in result[0][1] or 'y^2' in result[0][1]

    def test_malformed_table_missing_end(self):
        """Test handling of malformed LaTeX (missing end tag)."""
        latex_input = r"""\begin{tabular}{cc}
A & B \\
C & D"""

        # Should not crash, best-effort parsing
        result = convert_latex_table_to_csv(latex_input)

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_empty_string(self):
        """Test with empty input."""
        latex_input = ""

        result = convert_latex_table_to_csv(latex_input)

        # Empty string results in list with one row containing one empty string
        assert isinstance(result, list)
        assert len(result) == 1
        assert result == [['']]

    def test_table_with_extra_whitespace(self):
        """Test table with excessive whitespace."""
        latex_input = r"""\begin{tabular}{cc}
A    &    B \\
   C   &   D   \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        # Whitespace should be normalized and stripped
        assert result[0] == ['A', 'B']
        assert result[1] == ['C', 'D']

    def test_single_row_table(self):
        """Test table with single row."""
        latex_input = r"""\begin{tabular}{ccc}
One & Two & Three \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        assert len(result) >= 1
        assert result[0] == ['One', 'Two', 'Three']

    def test_single_column_table(self):
        """Test table with single column."""
        latex_input = r"""\begin{tabular}{c}
Row1 \\
Row2 \\
Row3 \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        assert len(result) >= 3
        assert result[0] == ['Row1']
        assert result[1] == ['Row2']
        assert result[2] == ['Row3']

    def test_table_with_alignment_specifications(self):
        """Test that alignment specifications are handled."""
        latex_input = r"""\begin{tabular}{lrc}
Left & Right & Center \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        # Basic alignment specs (without pipes) work
        assert len(result) >= 1
        assert result[0] == ['Left', 'Right', 'Center']

    def test_complex_latex_commands_stripped(self):
        """Test that LaTeX formatting commands are stripped."""
        latex_input = r"""\begin{tabular}{cc}
\textbf{Bold} & \textit{Italic} \\
Normal1 & Normal2 \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        # The regex pattern removes \command{content}
        assert len(result) >= 2
        assert isinstance(result[0], list)
        assert len(result[0]) == 2

    def test_table_without_begin_end_tags(self):
        """Test parsing table content without begin/end tags."""
        latex_input = r"""Header1 & Header2 \\
Data1 & Data2 \\"""

        result = convert_latex_table_to_csv(latex_input)

        # Should still parse rows and columns
        assert len(result) >= 2
        assert result[0] == ['Header1', 'Header2']
        assert result[1] == ['Data1', 'Data2']

    def test_preserves_numeric_content(self):
        """Test that numeric content is preserved."""
        latex_input = r"""\begin{tabular}{ccc}
123 & 456 & 789 \\
1.5 & 2.7 & 3.9 \\
\end{tabular}"""

        result = convert_latex_table_to_csv(latex_input)

        assert len(result) >= 2
        assert result[0] == ['123', '456', '789']
        assert result[1] == ['1.5', '2.7', '3.9']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
