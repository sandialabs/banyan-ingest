from openai import OpenAI
import base64
import io
from PIL import Image
import json

class NemotronOCR:
    """
    Wrapper class for Nemotron parse OCR functionality.
    Provides unified interface for OCR operations using Nemotron parse endpoint.
    """

    def __init__(self, endpoint_url="", model_name="nvidia/nemoretriever-parse"):
        """
        Initialize Nemotron OCR client.
        
        Args:
            endpoint_url: URL for Nemotron parse endpoint
            model_name: Model name to use for OCR
        """
        self.model_url = endpoint_url
        self.client = OpenAI(
            base_url=self.model_url,
            api_key="non-empty"  # Required but not used for local deployments
        )
        self.model = model_name

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
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image,
                        },
                    },
                ]
            }
        ]

        # Call Nemotron parse API
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                tools=[{"type": "function", "function": {"name": "markdown_bbox"}}],
                messages=messages,
                temperature=temperature
            )

            # Extract text from response
            tool_call = completion.choices[0].message.tool_calls[0]
            response = json.loads(tool_call.function.arguments)
            bbox_data = response[0]

            # Combine all text elements including all element types
            extracted_text = []
            for entry in bbox_data:
                # Include text from all element types
                extracted_text.append(entry['text'])

            return "\n".join(extracted_text)

        except Exception as e:
            print(f"Error performing OCR with Nemotron: {e}")
            return ""

    def get_detailed_ocr_results(self, base64_image: str, temperature: float = 0.0):
        """
        Get detailed OCR results including bounding boxes and element types.
        
        Args:
            base64_image: Base64 encoded image string
            temperature: Sampling temperature for the API request
            
        Returns:
            List of OCR result dictionaries with bounding box information
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image,
                        },
                    },
                ]
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                tools=[{"type": "function", "function": {"name": "markdown_bbox"}}],
                messages=messages,
                temperature=temperature
            )

            tool_call = completion.choices[0].message.tool_calls[0]
            response = json.loads(tool_call.function.arguments)
            return response[0]

        except Exception as e:
            print(f"Error getting detailed OCR results: {e}")
            return []