try:
    from .marker_processor import MarkerProcessor 
except:
    print("Marker not installed, cannot use MarkerProcessor")

try:
    from .papermage_processor import PaperMageProcessor
except:
    print("papermage not installed, cannot use PaperMageProcessor")

from .nemoparse_processor import NemoparseProcessor 

from .pptx_processor import PptxProcessor 
