import sys

from banyan_ingest import PptxProcessor

if __name__ == '__main__':
    filename = sys.argv[1]
    output_directory = sys.argv[2]
    output_base = sys.argv[3]

    document_processor = PptxProcessor()
    outputs = document_processor.process_document(filename)

    outputs.save_output(output_directory, output_base)

