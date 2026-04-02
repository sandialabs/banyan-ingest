import argparse
import os

from dotenv import load_dotenv, dotenv_values

from banyan_extract import NemoparseProcessor

try:
    from banyan_extract import MarkerProcessor
except:
    pass

try:
    from banyan_extract import PptxProcessor
except:
    pass

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", default=None, type=str, help="Path for a single file to be processed")
    parser.add_argument("output_dir", default=None, type=str, help="Path for output from single or multiple files")
    parser.add_argument("--is_input_dir", action="store_true",  help="Flags to set input file to directory")
    parser.add_argument("--output_base", default="banyan-extract-output", type=str,  help="Base name for output files")
    parser.add_argument("--backend", default="auto", type=str,  help="Which backend to use (auto (default)- auto-detect, nemoparse - Nemotron Parse, marker - marker, pptx - PPTX processor)")
    parser.add_argument("--config_file", default=".env", type=str,  help="Which config file to use (defaults to ./.env)")
    parser.add_argument("--endpoint", default="", type=str, help="Endpoint url for nemoretreiver-parse model")
    parser.add_argument("--model_name", default="", type=str, help="Endpoint url for nemoretreiver-parse model")
    parser.add_argument("--checkpointing", action="store_true", help="Flag where if true, then batch documents will be saved as they get processed")
    parser.add_argument("--draw_bboxes", action="store_true", default=False, help="Flag where if true, then ouptut will include images that show most bboxes found")
    parser.add_argument("--sort_by_position", action="store_true", default=True, help="Sort elements by spatial position for logical reading order")
    parser.add_argument("--re_run", action="store_true", default=False, help="Enables automatic retries. Uses contour area detection to evaluate missed regions, and re-runs the model at higher temperatures (max 3 retries) if the missed area is too high.")
    parser.add_argument("--temperature", default=0.0, type=float, help="Temperature setting for the model")
    parser.add_argument("--pptx_ocr_backend", default="surya", type=str,
                       help="OCR backend for PPTX processing (surya or nemotron)")
    parser.add_argument("--pptx_nemotron_endpoint", default="", type=str,
                       help="Nemotron endpoint URL for PPTX OCR")
    parser.add_argument("--pptx_nemotron_model", default="nvidia/nemoretriever-parse", type=str,
                       help="Nemotron model for PPTX OCR")
    return parser.parse_args()


def main():
    args = parse_arguments()

    output_directory = args.output_dir
    output_base = args.output_base
    endpoint = args.endpoint
    model_name = args.model_name
    backend = args.backend

    # Auto-detect backend based on file extension if backend is "auto"
    if args.backend == "auto":
        if args.is_input_dir:
            # For directories, we'll determine processor per file
            backend = "auto"
        else:
            # For single files, detect based on extension
            filename = args.input_file
            if filename.lower().endswith('.pptx'):
                backend = "pptx"
            elif filename.lower().endswith('.pdf'):
                backend = "nemoparse"
            else:
                backend = "nemoparse"  # Default to nemoparse for unknown types

    if backend == "nemoparse":
        if len(endpoint) == 0:
            config_values = dotenv_values(args.config_file)
            endpoint = config_values["NEMOPARSE_ENDPOINT"]
            model_name = config_values["NEMOPARSE_MODEL"]
            print(f"Using endpoint: {endpoint}")
            print(f"Using model: {model_name}")

        if endpoint != "":
            document_processor = NemoparseProcessor(endpoint_url=endpoint, model_name=model_name, sort_by_position=args.sort_by_position)
        else:
            raise Exception("Missing nemotron-parse endpoint url!")
    elif backend == "marker":
        document_processor = MarkerProcessor()
    elif backend == "pptx":
        document_processor = PptxProcessor(
            ocr_backend=args.pptx_ocr_backend,
            nemotron_endpoint=args.pptx_nemotron_endpoint or args.endpoint,
            nemotron_model=args.pptx_nemotron_model or args.model_name
        )

    if args.is_input_dir:
        input_directory = args.input_file

        file_paths = []
        basenames = []
        for root, _, files in os.walk(input_directory):
            for filename in files:
                file_paths.append(os.path.join(root, filename))
                basenames.append(os.path.basename(filename))

        # For auto mode with directories, determine processor per file
        if backend == "auto":
            for filepath, basename in zip(file_paths, basenames):
                # Determine processor based on file extension
                if filepath.lower().endswith('.pptx'):
                    processor = PptxProcessor(
                        ocr_backend=args.pptx_ocr_backend,
                        nemotron_endpoint=args.pptx_nemotron_endpoint or args.endpoint,
                        nemotron_model=args.pptx_nemotron_model or args.model_name
                    )
                else:  # Default to nemoparse for PDF and other files
                    if len(endpoint) == 0:
                        config_values = dotenv_values(args.config_file)
                        endpoint = config_values["NEMOPARSE_ENDPOINT"]
                        model_name = config_values["NEMOPARSE_MODEL"]
                    if endpoint != "":
                        processor = NemoparseProcessor(endpoint_url=endpoint, model_name=model_name, sort_by_position=args.sort_by_position)
                    else:
                        raise Exception("Missing nemotron-parse endpoint url!")

                # Process single file
                output = processor.process_document(filepath, re_run=args.re_run, temperature=args.temperature)
                if args.checkpointing:
                    output.save_output(output_directory, basename)
        else:
            # Use the selected processor for all files
            outputs = document_processor.process_batch_documents(file_paths, use_checkpointing=args.checkpointing, draw_bboxes=args.draw_bboxes, output_dir=output_directory, re_run=args.re_run, temperature=args.temperature)
            if not args.checkpointing:
                for file_output, basename in zip(outputs, basenames):
                    file_output.save_output(output_directory, basename)
    else:
        filename = args.input_file
        outputs = document_processor.process_document(filename, re_run=args.re_run, temperature=args.temperature)

        outputs.save_output(output_directory, output_base)


if __name__ == '__main__':
    main()