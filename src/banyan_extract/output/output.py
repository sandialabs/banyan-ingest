from abc import ABC, abstractmethod

class ModelOutput(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def save_output(self, output_directory, filename_base):
        pass
