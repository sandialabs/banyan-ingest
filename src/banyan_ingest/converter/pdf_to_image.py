import pdf2image

def convert_pdf_to_images(file_path, dpi=200):
    """
    Converts pdf to images
    Args:
        file_path (str): The path to the PDF file.
    Return:
        list of PIL images
    """
    return pdf2image.convert_from_path(file_path, dpi=dpi)

def convert_bytes_to_images(byte_stream, dpi=200):
    """
    Converts pdf byte stream to images
    Args:
        byte_stream (BytesIO): The byte-stream from the pdf
    Return:
        list of PIL images
    """
    return pdf2image.convert_from_bytes(byte_stream, dpi=dpi)
