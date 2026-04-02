try:
    from .marker_processor import MarkerProcessor 
except Exception as e:
    print(f"Marker not installed, cannot use MarkerProcessor, {e}")

try:
    from .papermage_processor import PaperMageProcessor
except:
    print("papermage not installed, cannot use PaperMageProcessor")

from .nemoparse_processor import NemoparseProcessor 
from .pptx_processor import PptxProcessor 
from .evaluate_extraction import evaluate_extraction