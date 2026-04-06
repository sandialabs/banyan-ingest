import sys
import argparse
import json
import base64
import io
import os
import tempfile

from typing import Union
from openai import OpenAI
from PIL import Image, ImageDraw

from .processor import Processor
from ..converter.pdf_to_image import convert_pdf_to_images, convert_bytes_to_images
from ..output.nemoparse_output import NemoparseData, NemoparseOutput
from ..ocr.nemotron_ocr import NemotronOCR

from .evaluate_extraction import evaluate_extraction
from ..utils.image_rotation import rotate_image, is_valid_rotation_angle

class NemoparseProcessor(Processor):

    def __init__(self, endpoint_url="", model_name="nvidia/nemoretriever-parse", sort_by_position=True):
        super().__init__()
        self.nemotron_ocr = NemotronOCR(
            endpoint_url=endpoint_url,
            model_name=model_name
        )
        self.sort_by_position = sort_by_position

    def sort_elements_by_position(self, bbox_data, width, height):
        """
        Sort document elements based on their spatial position.

        Args:
            bbox_data: List of element dictionaries from API response
            width: Page width in pixels
            height: Page height in pixels

        Returns:
            List of sorted element dictionaries
        """
        def get_sort_key(element):
            bbox = element['bbox']
            # Convert normalized coordinates to absolute pixels
            # Use top-left corner (ymin, xmin) instead of center for better reading order
            y_top = bbox['ymin'] * height
            x_left = bbox['xmin'] * width

            # Element type priority (headers first, then text, then other elements)
            type_priority = {
                'Section-header': 0,
                'Text': 1,
                'Formula': 2,
                'Code': 3,
                'Picture': 4,
                'Table': 5,
                'Caption': 6
            }.get(element['type'], 7)

            return (y_top, x_left, type_priority)

        return sorted(bbox_data, key=get_sort_key)

    def _encode_image(self, image):
        try:
            base64_encoded_data = base64.b64encode(image)
            base64_string = base64_encoded_data.decode("utf-8")
            return base64_string
        except Exception as e:
            print(f"An error occurred trying to encode the document: {e}")
            return None

    def _run_single_ocr_pass(self, image, draw_bboxes=True, temperature=0.0, rotation_angle: float = 0):
        
        if rotation_angle != 0:
            image = rotate_image(Image.open(io.BytesIO(image)), rotation_angle)
            # Convert back to bytes for processing
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            image = img_byte_arr.getvalue()

        base64_string = self._encode_image(image)
        base64_image = f"data:image/png;base64,{base64_string}"

        # Use the wrapper for image processing with temperature
        bbox_data = self.nemotron_ocr.get_detailed_ocr_results(base64_image, temperature=temperature)

        base_image = Image.open(io.BytesIO(image))
        width, height = base_image.size

        # Sort elements by spatial position if enabled
        if self.sort_by_position:
            bbox_data = self.sort_elements_by_position(bbox_data, width, height)

        if draw_bboxes:
            bbox_draw = ImageDraw.Draw(base_image)
            color_dict = {
                        "Text": "red",
                        "Formula": "green",
                        "Code": "blue",
                        "Picture": "magenta",
                        "Table": "cyan",
                        "Caption": "yellow",
                        }

        txt = []
        images = []
        tables = []

        for entry in bbox_data:
            bbox = entry['bbox']
            xmin = bbox['xmin'] * width
            ymin = bbox['ymin'] * height
            xmax = bbox['xmax'] * width
            ymax = bbox['ymax'] * height

            element_text = entry['text']
            if entry['type'] in "Picture":
                cropped_image = base_image.crop((xmin, ymin, xmax, ymax))
                images.append(cropped_image)
                element_text = "![{}]({})"
            elif entry ['type'] in "Table":
                tables.append(entry['text'])
            elif entry['type'] in "Section-header" and "#" not in entry['text']:
                element_text = f"# {entry['text']}"

            txt.append(element_text)

            if draw_bboxes:
                if entry['type'] in color_dict:
                    color = color_dict[entry['type']]
                    if ymin > ymax:
                        ymin, ymax = ymax, ymin
                    if xmin > xmax:
                        xmin, xmax = xmax, xmin
                    bbox_draw.rectangle([xmin, ymin, xmax, ymax], outline=color, width=4)

        return NemoparseData(text=txt, bbox_json=bbox_data, images=images, tables=tables, bbox_image=base_image) 

    def _process_image(self, image, temperature=0.0, draw_bboxes=True, re_run=False, re_run_temp=0.4):
        print(f"\nRunning with temperature {temperature}")
        output = self._run_single_ocr_pass(image, draw_bboxes=draw_bboxes, temperature=temperature)

        if not re_run:
            return output

        # Evaluate the initial pass to get our starting metrics
        should_rerun, missed_percentage = evaluate_extraction(
            image_bytes=image,
            bbox_data=output.bbox_json,
            temperature=temperature
        )

        # Set the baseline for the best performing run
        best_output = output
        lowest_missed = missed_percentage

        if not should_rerun:
            print("Initial pass meets criteria. Proceeding with current output.")
            return best_output

        print("Initial pass flagged for improvement. Initiating retry loop.")
        attempts = 0
        max_attempts = 3
        
        while attempts < max_attempts:
            attempts += 1
            print(f"\n*** Retry Attempt {attempts} of {max_attempts} (Temp: {re_run_temp}) ***")
            
            # Generate new output
            current_output = self._run_single_ocr_pass(image, draw_bboxes=draw_bboxes, temperature=re_run_temp)
            
            # Evaluate the new output
            should_rerun, missed_percentage = evaluate_extraction(
                image_bytes=image,
                bbox_data=current_output.bbox_json,
                temperature=re_run_temp
            )

            # Compare and save the run with the lowest missed percentage
            if missed_percentage < lowest_missed:
                lowest_missed = missed_percentage
                best_output = current_output

            # Stop retrying if we hit a successful threshold
            if not should_rerun:
                print(f"Retry {attempts} successful. Breaking loop.")
                break
                
            # Log when we hit the absolute limit
            if attempts == max_attempts:
                print(f"Max retries exhausted. Returning best attempt with {lowest_missed:.1f}% missed area.")

        # Return whichever output performed best across all runs
        return best_output

    def get_pages(self, filepath):
        file_pages = []
        if isinstance(filepath, io.BytesIO):
            images = convert_bytes_to_images(filepath.read())
            for image in images:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                file_pages.append(img_byte_arr)
        else:
            if "png" in filepath or "tif" in filepath or "TIF" in filepath:
                with open(filepath, "rb") as image_file:
                    file_pages.append(image_file.read())
            elif "pdf" in filepath:
                images = convert_pdf_to_images(filepath)
                for image in images:
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    img_byte_arr = img_byte_arr.getvalue()
                    file_pages.append(img_byte_arr)
            else:
                try:
                    images = convert_pdf_to_images(filepath)
                    for image in images:
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='PNG')
                        img_byte_arr = img_byte_arr.getvalue()
                        file_pages.append(img_byte_arr)
                except:
                    raise Exception(f"Unsupported filetype! {filepath}")
        return file_pages

    def process_batch_documents(self, filepaths, use_checkpointing=True, draw_bboxes=True, output_dir="./", re_run=False, temperature=0.0, rotation_angle: Union[int, float] = 0):
        file_outputs = []
        for filepath in filepaths:
            output = self.process_document(filepath, draw_bboxes=draw_bboxes, re_run=re_run, temperature=temperature, rotation_angle=rotation_angle)
            if use_checkpointing:
                basename = os.path.basename(filepath)
                print(basename)
                output.save_output(output_dir, basename)
            else:
                file_outputs.append(output)

        return file_outputs

    def process_page(self, page, re_run=False, temperature=0.0, rotation_angle: float = 0):
        return self._process_image(page, re_run=re_run, temperature=temperature, rotation_angle=rotation_angle)

    def process_document(self, filepath, draw_bboxes=True, re_run=False, temperature=0.0, rotation_angle: Union[int, float] = 0):
        # Basic check of file type
        file_pages = self.get_pages(filepath) 

        # Validate rotation angle
        if not is_valid_rotation_angle(rotation_angle):
            raise ValueError(f"Invalid rotation angle: {rotation_angle}")
        
        # Normalize rotation angle
        from ..utils.image_rotation import normalize_rotation_angle
        normalized_angle = normalize_rotation_angle(rotation_angle)

        output = NemoparseOutput()
        for page_image in file_pages:
            output.add_output(self._process_image(page_image, temperature=temperature, draw_bboxes=draw_bboxes, re_run=re_run, rotation_angle=normalized_angle))
        return output