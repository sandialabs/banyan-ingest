from abc import ABC, abstractmethod

class Processor(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def process_document(self, filepath):
        pass

    @abstractmethod
    def process_batch_documents(self, filepaths):
        pass
