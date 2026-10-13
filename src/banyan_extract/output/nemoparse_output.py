import csv 
import os
import json

from PIL import Image, ImageDraw
from dataclasses import dataclass

from .output import ModelOutput
from ..converter import convert_latex_table_to_csv


@dataclass
class NemoparseData:
    text: list 
    bbox_json: str
    images: list
    tables: list
    bbox_image: Image
    page_number: int


class NemoparseOutput(ModelOutput):

    def __init__(self):
        super().__init__()
        self.text: list[str] = []
        self.images: list[list] = []
        self.tables: list[list] = []
        self.bboxdata: list[str] = []
        self.bbox_image: list[Image] = []
        self.page_number_list: list[int] = []
        
    def add_output(self, output_data):
        self.text.append(output_data.text)
        self.images.append(output_data.images)
        self.tables.append(output_data.tables)
        self.bboxdata.append(output_data.bbox_json)
        self.bbox_image.append(output_data.bbox_image)
        self.page_number_list.append(output_data.page_number)

    def _page_number_at(self, idx):
        """Return the page number for the page at position idx (1-based fallback)."""
        if idx < len(self.page_number_list) and self.page_number_list[idx] is not None:
            return self.page_number_list[idx]
        return idx + 1

    def _build_markdown(self, img_filenames):
        """
        Build the markdown document with a '# <PAGE N>' header before each page.

        Returns:
            (markdown_string, line_ranges) where line_ranges[i] is a
            (start, end) tuple of 0-based line indices for page i, with
            start inclusive and end exclusive.
        """
        page_blocks = []
        line_ranges = []
        current_line = 0
        img_index = 0
        for idx, text_list in enumerate(self.text):
            parts = [f"[//]: # <PAGE {self._page_number_at(idx)}>"]
            for text in text_list:
                if "![{}]({})" in text:
                    text = text.format(f"Image {img_index}", img_filenames[img_index])
                    img_index += 1
                parts.append(text)
            block = "\n\n".join(parts)
            page_blocks.append(block)

            block_lines = block.count("\n") + 1
            line_ranges.append((current_line, current_line + block_lines))
            # Account for the blank line separating this page from the next
            current_line += block_lines + 1

        markdown = "\n\n".join(page_blocks)
        if markdown:
            markdown += "\n"
        return markdown, line_ranges

    def _build_bbox_pages(self):
        """Return bbox data grouped by page: [{"page": N, "content": [...]}, ...]."""
        return [
            {"page": self._page_number_at(idx), "content": bboxdata}
            for idx, bboxdata in enumerate(self.bboxdata)
        ]

    @classmethod
    def get_output_path(cls, output_directory, filename_base):
        return os.path.join(output_directory, f"{filename_base}.md")
        
    def save_output(self, output_directory, filename_base, save_images=False,
                    save_bbox_data=False, save_tables=False, save_page_numbers=False):
        img_index = 0
        img_filenames = []
        for image_list in self.images:
            for img in image_list:
                img_filename = f"{filename_base}_image_{img_index}.png"
                if save_images:
                    try:
                        img.save(os.path.join(output_directory, img_filename))
                    except Exception as e:
                        print(f"An error occurred trying to save the image: {img_filename}: {e}")

                img_index += 1
                img_filenames.append(img_filename)

        if save_bbox_data:
            with open(
                os.path.join(output_directory, f"{filename_base}_bbox.json"),
                "w+") as f:
                json.dump(self._build_bbox_pages(), f, indent=4)
                f.write("\n")

            for index, bbox_image in enumerate(self.bbox_image):
                bbox_image.save(os.path.join(output_directory, f"{filename_base}_bbox_image_{index}.png"))

        if save_tables:
            table_index = 0
            for table_list in self.tables:
                for table in table_list:
                    table_name = f"{filename_base}_table_{table_index}.csv"
                    converted_table = convert_latex_table_to_csv(table)

                    with open(os.path.join(output_directory, table_name), 'w') as csv_file:
                        csv_writer = csv.writer(csv_file)
                        for row in converted_table:
                            csv_writer.writerow(row)

                    table_index += 1

        # Write final markdown output
        markdown, line_ranges = self._build_markdown(img_filenames)
        with open(
            os.path.join(output_directory, f"{filename_base}.md"), "w+") as f:
            f.write(markdown)

        if save_page_numbers:
            with open(
                os.path.join(output_directory, f"{filename_base}.metadata"), "w") as f:
                f.write("Page_Number,Markdown_Lines\n")
                for idx, (text_start, text_end) in enumerate(line_ranges):
                    page_num = self._page_number_at(idx)
                    f.write(f"{page_num},{text_start}-{text_end}\n")

    def return_bytes(self, output_directory, filename_base, save_images=False,
                     save_bbox_data=False, save_tables=False, save_page_numbers=False):

        bytes_return_dict = dict()
        encoding = "utf-8"

        bytes_return_dict["encoding"] = encoding
        
        img_index = 0
        img_filenames = []
        image_bytes_list = []
        for image_list in self.images:
            for img in image_list:
                img_filename = f"{filename_base}_image_{img_index}.png"
                if save_images:
                    image_bytes_list.append(img)

                img_index += 1
                img_filenames.append(img_filename)

        if save_images:
            bytes_return_dict["images"] = image_bytes_list
            bytes_return_dict["image_filenames"] = img_filenames

        if save_bbox_data:

            bbox_summary_string = json.dumps(self._build_bbox_pages(), indent=4) + "\n"

            bbox_summary = bbox_summary_string.encode(encoding)
            bytes_return_dict["bbox_summary"] = bbox_summary

            bbox_bytes_list = []            
            for index, bbox_image in enumerate(self.bbox_image):
                bbox_bytes_list.append(bbox_image)
            bytes_return_dict["bbox_images"] = bbox_bytes_list
        
        if save_tables:
            table_index = 0

            table_bytes_list = []            
            for table_list in self.tables:
                for table in table_list:
                    table_name = f"{filename_base}_table_{table_index}.csv"
                    converted_table = convert_latex_table_to_csv(table)

                    #with open(os.path.join(output_directory, table_name), 'w') as csv_file:
                    #    csv_writer = csv.writer(csv_file)
                    #    for row in converted_table:
                    #        csv_writer.writerow(row)

                    if isinstance(converted_table, list):
                        #print(f"converted_table: {type(converted_table)}")
                        #print(f"converted_table: {converted_table}")
                        #print(f"converted_table: {'\n'.join(converted_table)}")
                        #table_string = "\n".join(converted_table) + "\n"
                        table_string = ""
                        for row in converted_table:
                            row_string = ",".join(row) + "\n"
                            table_string += row_string

                    elif isinstance(converted_table, str):
                        table_string = converted_table
                    else:
                        raise NotImplementedError(f"\n[*] ERROR: unexpected type '{type(converted_table)}' for converted_table encountered...\n")

                    table_bytes_list.append(table_string.encode(encoding))

                    table_index += 1

            bytes_return_dict["tables"] = table_bytes_list

        raw_markdown_string, line_ranges = self._build_markdown(img_filenames)
        bytes_return_dict["markdown"] = raw_markdown_string.encode(encoding)

        if save_page_numbers:
            bytes_return_dict["page_number_lines"] = [
                (self._page_number_at(idx), line_range)
                for idx, line_range in enumerate(line_ranges)
            ]

        return bytes_return_dict
            

    def get_bbox_output(self, with_bbox_data=True):
        dict_data = {}
        for i, data in enumerate(self.bboxdata):
            if with_bbox_data:
                dict_data[f"page_{i}"] = data
            else:
                tmp_data = []
                for entry in data:
                    tmp_entry = {}
                    for key in entry:
                        if key != "bbox":
                            tmp_entry[key] = entry[key]
                    tmp_data.append(tmp_entry)
                dict_data[f"page_{i}"] = tmp_data
        return dict_data
        #return self.bboxdata

    def get_output_as_json(self, with_bbox_data=True):
        if with_bbox_data:
            return json.dumps(self.bboxdata)
        else:
            cleaned_data = []
            for bboxdata in self.bboxdata:
                tmp_data = []
                for entry in bboxdata:
                    tmp_entry = {}
                    for key in entry:
                        if key != "bbox":
                            tmp_entry[key] = entry[key]
                    tmp_data.append(tmp_entry)
                cleaned_data.append(tmp_data)
            return json.dumps(cleaned_data)

    def get_output_as_markdown(self):
        num_images = sum(len(image_list) for image_list in self.images)
        num_placeholders = sum(
            1 for text_list in self.text for text in text_list if "![{}]({})" in text
        )
        img_filenames = [f"image_{i}.png" for i in range(max(num_images, num_placeholders))]
        markdown, _ = self._build_markdown(img_filenames)
        return markdown

    def get_content_list(self):
        content = []
        for page_text in self.text:
            tmp_data = ""
            for text in page_text:
                tmp_data += text
            content.append(tmp_data)
        return content

    def get_images(self):
        images = []
        for image_list in self.images:
            for img in image_list:
                images.append(img)
        
        return images

    def get_output_status(self):
        no_outputs = []
