import base64
import io
import json
import os
import re
from enum import Enum
from urllib.parse import urlsplit

import httpx
from openai import OpenAI
from PIL import Image


class ModelVersion(Enum):
    LEGACY = 'legacy' 
    LATEST = 'latest' # 1.2

    def __str__(self):
        return self.value


def extract_bbox_data_from_response(text: str):
    _re_extract_class_bbox = re.compile(r'<x_(\d+(?:\.\d+)?)><y_(\d+(?:\.\d+)?)>(.*?)<x_(\d+(?:\.\d+)?)><y_(\d+(?:\.\d+)?)><class_([^>]+)>', re.DOTALL)

    bbox_data = []

    for m in _re_extract_class_bbox.finditer(text):
        x1, y1, text, x2, y2, cls = m.groups()

        entry = {
                "type": cls,
                "text": text,
                "bbox": {
                    "xmin": float(x1),
                    "ymin": float(y1),
                    "xmax": float(x2),
                    "ymax": float(y2)
                    }
                }
        bbox_data.append(entry)

    return bbox_data


def is_parse_endpoint(endpoint_url: str) -> bool:
    """Identify a complete document Parse API URL by its final path segment."""
    return urlsplit(endpoint_url).path.rstrip("/").endswith("/parse")


class NemotronOCR:
    """
    Wrapper class for Nemotron parse OCR functionality.
    Provides unified interface for OCR operations using Nemotron parse endpoint.
    """

    def __init__(
        self,
        endpoint_url: str = "",
        model_name: str = "nvidia/NVIDIA-Nemotron-Parse-v1.2",
        model_version: ModelVersion = ModelVersion.LATEST,
        api_key: str | None = None,
    ) -> None:
        """
        Initialize Nemotron OCR client.
        
        Args:
            endpoint_url: Complete Parse API URL or OpenAI-compatible base URL.
            model_name: Model identifier for OpenAI-compatible deployments.
            model_version: Response format for OpenAI-compatible deployments.
            api_key: Optional bearer credential for the configured endpoint.
        """
        self.model_url = endpoint_url
        self.model = model_name
        self.model_version = model_version
        self.uses_parse_api = is_parse_endpoint(endpoint_url)
        if self.uses_parse_api and urlsplit(endpoint_url).hostname == "ai.api.nvidia.com":
            api_key = api_key or os.getenv("NEMOPARSE_API_KEY")
            if not api_key:
                raise ValueError("Set NEMOPARSE_API_KEY to use the NVIDIA-hosted Parse API.")
        self.api_key = api_key
        self.client = None if self.uses_parse_api else OpenAI(base_url=endpoint_url, api_key=api_key or "non-empty")

    def validate_sampling(self, temperature: float, re_run: bool = False) -> None:
        """Reject sampling controls that the document Parse API cannot apply."""
        if self.uses_parse_api and (temperature != 0.0 or re_run):
            raise ValueError("The Parse API does not support --temperature or --re_run.")

    def _parse_document(self, base64_image: str) -> list[dict]:
        _, separator, payload = base64_image.partition(";base64,")
        if not separator:
            raise ValueError("The Parse API needs a base64 data URL for one page image.")
        image_bytes = base64.b64decode(payload, validate=True)
        # The caller may label raw JPEG or TIFF bytes as PNG. Use the real format.
        with Image.open(io.BytesIO(image_bytes)) as image:
            if image.format == "JPEG":
                document = ("page.jpg", image_bytes, "image/jpeg")
            else:
                if image.format != "PNG":
                    png = io.BytesIO()
                    image.convert("RGB").save(png, format="PNG")
                    image_bytes = png.getvalue()
                document = ("page.png", image_bytes, "image/png")

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = httpx.post(self.model_url, headers=headers, files={"document": document}, timeout=120.0)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or not isinstance(result.get("content"), str):
            raise ValueError("The Parse API response is missing text content.")
        if result.get("finish_reason") == "length":
            raise ValueError("The Parse API hit its output token limit. Try a smaller page crop.")
        return extract_bbox_data_from_response(result["content"])

    def _get_response(self, base64_image: str, temperature: float = 0.0) -> list[dict]:
        if self.uses_parse_api:
            self.validate_sampling(temperature)
            return self._parse_document(base64_image)

        content = []
        tools = []
        extra_body = {}
        if self.model_version == ModelVersion.LATEST:
            prompt_text = "</s><s><predict_bbox><predict_classes><output_markdown><predict_no_text_in_pic>"
            content.append({
                            "type": "text",
                            "text": prompt_text,
                            })

            extra_body["repetition_penalty"] = 1.1
            extra_body["top_k"] = 1
            extra_body["skip_special_tokens"] = False
        else:
            tools.append({"type": "function", "function": {"name": "markdown_bbox"}})

        content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image,
                            }
                        })

        messages = [
            {
                "role": "user",
                "content": content,
            }
        ]

        completion_args = {
                    'model': self.model,
                    'messages': messages,
                    'temperature': temperature,
                    }

        if self.model_version == ModelVersion.LATEST:
            completion_args['extra_body'] = extra_body
        else:
            completion_args['tools'] = tools

        try:
            completion = self.client.chat.completions.create(
                #model=self.model,
                #tools=tools,
                #messages=messages,
                #temperature=temperature,
                #extra_body=extra_body,
                **completion_args
            )

            if self.model_version == ModelVersion.LATEST:
                response = completion.choices[0].message.content

                return extract_bbox_data_from_response(response)
            else:
                tool_call = completion.choices[0].message.tool_calls[0]
                response = json.loads(tool_call.function.arguments)

                return response[0]
        except Exception as e:
            print(f"Error getting detailed OCR results: {e}")
            raise

    def ocr_image(self, image: Image.Image, temperature: float = 0.0) -> str:
        """
        Perform OCR on a single image using Nemotron parse endpoint.
        
        Args:
            image: PIL Image object to perform OCR on
            temperature: Sampling temperature for the API request
            
        Returns:
            Extracted text from the image
        """
        # Convert image to base64
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        base64_encoded_data = base64.b64encode(img_byte_arr)
        base64_string = base64_encoded_data.decode("utf-8")
        base64_image = f"data:image/png;base64,{base64_string}"

        # Prepare API request
        bbox_data = self._get_response(base64_image, temperature=temperature)

        # Combine all text elements including all element types
        extracted_text = []
        for entry in bbox_data:
            # Include text from all element types
            extracted_text.append(entry['text'])

        return "\n".join(extracted_text)

    def get_detailed_ocr_results(self, base64_image: str, temperature: float = 0.0):
        """
        Get detailed OCR results including bounding boxes and element types.
        
        Args:
            base64_image: Base64 encoded image string
            temperature: Sampling temperature for the API request
            
        Returns:
            List of OCR result dictionaries with bounding box information
        """
        return self._get_response(base64_image, temperature=temperature)
