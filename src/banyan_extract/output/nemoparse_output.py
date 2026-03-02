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


class NemoparseOutput(ModelOutput):

    def __init__(self):
        super().__init__()
        self.text: list[str] = []
        self.images: list[list] = []
        self.tables: list[list] = []
        self.bboxdata: list[str] = []
        self.bbox_image: list[Image] = []
        
    def add_output(self, output_data):
        self.text.append(output_data.text)
        self.images.append(output_data.images)
        self.tables.append(output_data.tables)
        self.bboxdata.append(output_data.bbox_json)
        self.bbox_image.append(output_data.bbox_image)

    def save_output(self, output_directory, filename_base):
        img_index = 0
        img_filenames = []
        for image_list in self.images:
            for img in image_list:
                img_filename = f"{filename_base}_image_{img_index}.png"
                try:
                    img.save(os.path.join(output_directory, img_filename))
                except Exception as e:
                    print(f"An error occurred trying to save the image: {img_filename}: {e}")

                img_index += 1
                img_filenames.append(img_filename)

        with open(
            os.path.join(output_directory, f"{filename_base}.md"), "w+") as f:
            img_index = 0
            for text_list in self.text:
                for text in text_list:
                    if "![{}]({})" in text:
                        text = text.format(f"Image {img_index}", img_filenames[img_index])
                        img_index += 1
                    f.write(text + "\n\n")
                f.write("\n")

        with open(
            os.path.join(output_directory, f"{filename_base}_bbox.json"),
            "w+") as f:
            for bboxdata in self.bboxdata:
                f.write(json.dumps(bboxdata, indent=2))

        for index, bbox_image in enumerate(self.bbox_image):
            bbox_image.save(os.path.join(output_directory, f"{filename_base}_bbox_image_{index}.png"))

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
                for entry in data:
                    tmp_entry = {}
                    for key in entry:
                        if key != "bbox":
                            tmp_entry[key] = entry[key]
                    tmp_data.append(tmp_entry)
                cleaned_data.append(tmp_data)
            return json.dumps(cleaned_data)

    def get_output_as_markdown(self):
        full_text = ""
        for page_text in self.text:
            for text in page_text:
                full_text += text
            full_text += "\n"
        return full_text
