import pandas as pd

from marker.models import create_model_dict
from marker.settings import settings
from marker.converters.pdf import PdfConverter
from marker.schema.document import Document
from marker.renderers.markdown import MarkdownRenderer
from marker.renderers.markdown import Markdownify
from marker.renderers.markdown import get_formatted_table_text, cleanup_text

from typing import Annotated, Any, Dict, List, Optional, Type, Tuple
from collections import defaultdict
from bs4 import NavigableString
from pydantic import BaseModel

from .processor import Processor
from ..output.marker_output import MarkerOutput


class CustomMarkdownify(Markdownify):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tables = []

    def convert_table(self, el, text, parent_tags):
        total_rows = len(el.find_all('tr'))
        colspans = []
        rowspan_cols = defaultdict(int)
        for i, row in enumerate(el.find_all('tr')):
            row_cols = rowspan_cols[i]
            for cell in row.find_all(['td', 'th']):
                colspan = int(cell.get('colspan', 1))
                row_cols += colspan
                for r in range(int(cell.get('rowspan', 1)) - 1):
                    rowspan_cols[i + r] += colspan # Add the colspan to the next rows, so they get the correct number of columns
            colspans.append(row_cols)
        total_cols = max(colspans) if colspans else 0

        grid = [[None for _ in range(total_cols)] for _ in range(total_rows)]

        for row_idx, tr in enumerate(el.find_all('tr')):
            col_idx = 0
            for cell in tr.find_all(['td', 'th']):
                # Skip filled positions
                while col_idx < total_cols and grid[row_idx][col_idx] is not None:
                    col_idx += 1

                # Fill in grid
                value = get_formatted_table_text(cell).replace("\n", " ").replace("|", " ").strip()
                rowspan = int(cell.get('rowspan', 1))
                colspan = int(cell.get('colspan', 1))

                if col_idx >= total_cols:
                    # Skip this cell if we're out of bounds
                    continue

                for r in range(rowspan):
                    for c in range(colspan):
                        try:
                            if r == 0 and c == 0:
                                grid[row_idx][col_idx] = value
                            else:
                                grid[row_idx + r][col_idx + c] = '' # Empty cell due to rowspan/colspan
                        except IndexError:
                            # Sometimes the colspan/rowspan predictions can overflow
                            print(f"Overflow in columns: {col_idx + c} >= {total_cols} or rows: {row_idx + r} >= {total_rows}")
                            continue

                col_idx += colspan

        self.tables.append(pd.DataFrame.from_dict(grid))

        markdown_lines = []
        col_widths = [0] * total_cols
        for row in grid:
            for col_idx, cell in enumerate(row):
                if cell is not None:
                    col_widths[col_idx] = max(col_widths[col_idx], len(str(cell)))

        add_header_line = lambda: markdown_lines.append('|' + '|'.join('-' * (width + 2) for width in col_widths) + '|')

        # Generate markdown rows
        added_header = False
        for i, row in enumerate(grid):
            is_empty_line = all(not cell for cell in row)
            if is_empty_line and not added_header:
                # Skip leading blank lines
                continue

            line = []
            for col_idx, cell in enumerate(row):
                if cell is None:
                    cell = ''
                padding = col_widths[col_idx] - len(str(cell))
                line.append(f" {cell}{' ' * padding} ")
            markdown_lines.append('|' + '|'.join(line) + '|')

            if not added_header:
                # Skip empty lines when adding the header row
                add_header_line()
                added_header = True

        # Handle one row tables
        if total_rows == 1:
            add_header_line()

        table_md = '\n'.join(markdown_lines)
        return "\n\n" + table_md + "\n\n"


class CustomMarkdownOutput(BaseModel):
    markdown: str
    images: dict
    metadata: dict
    tables: list


class CustomMarkdownRenderer(MarkdownRenderer):
    page_separator: Annotated[str, "The separator to use between pages.", "Default is '-' * 48."] = "-" * 48
    inline_math_delimiters: Annotated[Tuple[str], "The delimiters to use for inline math."] = ("$", "$")
    block_math_delimiters: Annotated[Tuple[str], "The delimiters to use for block math."] = ("$$", "$$")

    #paginate_output, page_separator, inline_math_delimiters, block_math_delimiters
    @property
    def md_cls(self):
        return CustomMarkdownify(
            paginate_output=self.paginate_output,
            page_separator=self.page_separator,
            heading_style="ATX",
            bullets="-",
            escape_misc=False,
            escape_underscores=True,
            escape_asterisks=True,
            escape_dollars=True,
            sub_symbol="<sub>",
            sup_symbol="<sup>",
            inline_math_delimiters=self.inline_math_delimiters,
            block_math_delimiters=self.block_math_delimiters,
            html_tables_in_markdown=False
        )

    def __call__(self, document: Document) -> CustomMarkdownOutput:
        document_output = document.render()
        full_html, images = self.extract_html(document, document_output)
        _md_cls = self.md_cls
        markdown = _md_cls.convert(full_html)
        markdown = cleanup_text(markdown)
        tables = _md_cls.tables
        return CustomMarkdownOutput(
            markdown=markdown,
            images=images,
            metadata=self.generate_document_metadata(document, document_output),
            tables=tables
        )


class CustomPdfConverter(PdfConverter):
    """
    A converter for processing and rendering PDF files into Markdown, JSON, HTML and other formats.
    """
    def __init__(
        self,
        artifact_dict: Dict[str, Any],
        renderer = None, 
        processor_list: Optional[List[str]] = None,
        llm_service: str | None = None,
        config=None,
    ):
        super().__init__(
                        artifact_dict=artifact_dict,
                        processor_list=processor_list,
                        renderer=renderer if isinstance(renderer, str) else None,
                        llm_service=llm_service,
                        config=config)

        if (not isinstance(renderer, str)) and (renderer is not None):
            self.renderer = renderer


class MarkerProcessor(Processor):
    
    def __init__(self):
        super().__init__()
        models = create_model_dict()
        config = {}
        config["format_lines"] = True
        config["force_ocr"] = True
        self.converter = CustomPdfConverter(
                        artifact_dict = models,
                        renderer=CustomMarkdownRenderer,
                        config=config,
                        )

    def process_document(self, filepath):
        output = self.converter(filepath)
        return MarkerOutput(output)

    def process_batch_documents(self, filepaths):
        file_outputs = []
        for filepath in filepaths:
            output = self.process_document(filepath)
            file_outputs.append(output)
            #try:
            #    output = self.process_document(filepath)
            #    file_outputs.append(output)
            #except:
            #    print(f"Failed to parse document: {filepath}")

        return file_outputs
