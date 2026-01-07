import sys
import argparse
import json
import base64
import io

from openai import OpenAI
from PIL import Image, ImageDraw

from .processor import Processor
from ..converter.pdf_to_image import convert_pdf_to_images
from ..output.nemoparse_output import NemoparseData, NemoparseOutput

class NemoparseProcessor(Processor):
    
    def __init__(self, endpoint_url="", model_name="nvidia/nemoretriever-parse"):
        super().__init__()
        self.model_url = endpoint_url
        self.client = OpenAI(
              base_url = self.model_url,
              # For local deployment, an API key is not needed but the following string
              # varible should be non-empty.
              api_key = "non-empty"
            )
        self.model=model_name

    def _encode_image(self, image):
        try:
            base64_encoded_data = base64.b64encode(image)
            base64_string = base64_encoded_data.decode("utf-8")
            return base64_string
        except Exception as e:
            print(f"An error occurred trying to encode the document: {e}")
            return None

    def _process_image(self, image):
        base64_string = self._encode_image(image)
        base64_image = f"data:image/png;base64,{base64_string}"
        messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                # You can provide the image URL or send the image
                                # data as a Base64-encoded string.
                                "url": base64_image,
                            },
                        },
                    ]
                }
            ]

        completion = self.client.chat.completions.create(
            model=self.model,
            # See Tool types section for more information.
            tools=[{"type": "function", "function": {"name": "markdown_bbox"}}],
            messages=messages
        )

        tool_call = completion.choices[0].message.tool_calls[0]
        response = json.loads(tool_call.function.arguments)

        bbox_data = response[0]

        base_image = Image.open(io.BytesIO(image))
        width, height = base_image.size

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

            if entry['type'] in color_dict:
                color = color_dict[entry['type']]
                if ymin > ymax:
                    ymin, ymax = ymax, ymin
                bbox_draw.rectangle([xmin, ymin, xmax, ymax], outline=color, width=4)
        #markdown_output = "\n".join(txt)

        return NemoparseData(text=txt, bbox_json=bbox_data, images=images, tables=tables, bbox_image=base_image) 

    def process_document(self, filepath):
        # Basic check of file type
        file_pages = []
        if "png" in filepath:
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

        output = NemoparseOutput()
        for page_image in file_pages:
            output.add_output(self._process_image(page_image))
        return output

    def process_batch_documents(self, filepaths):
        file_outputs = []
        for filepath in filepaths:
            output = self.process_document(filepath)
            file_outputs.append(output)

        return file_outputs
