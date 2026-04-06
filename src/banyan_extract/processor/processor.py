from abc import ABC, abstractmethod
from typing import Union, List, Optional

class Processor(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def process_document(self, filepath, rotation_angle: Union[int, float] = 0):
        """
        Process a single document with optional rotation.
        
        Args:
            filepath: Path to the document file
            rotation_angle: Rotation angle in degrees (default: 0)
        """
        pass

    @abstractmethod
    def process_batch_documents(self, filepaths, rotation_angle: Union[int, float] = 0):
        """
        Process multiple documents with optional rotation.
        
        Args:
            filepaths: List of paths to document files
            rotation_angle: Rotation angle in degrees (default: 0)
        """
        pass
