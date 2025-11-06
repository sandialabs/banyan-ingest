import pdf2image

def convert_pdf_to_images(file_path, dpi=200):
    """
    Extracts text from a PDF file using Tesseract-OCR.
    Args:
        file_path (str): The path to the PDF file.
    Return:
        list of PIL images
    """
    return pdf2image.convert_from_path(file_path, dpi=dpi)
