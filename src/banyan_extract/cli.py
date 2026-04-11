import argparse
import os
import sys
import logging

from dotenv import load_dotenv, dotenv_values

from banyan_extract import NemoparseProcessor

try:
    from banyan_extract import MarkerProcessor
except ImportError:
    pass

try:
    from banyan_extract import PptxProcessor
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def validate_file_exists(filepath):
    """Validate that a file exists and is readable."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    if not os.access(filepath, os.R_OK):
        raise PermissionError(f"File not readable: {filepath}")


def validate_directory_writable(directory):
    """Validate that a directory exists and is writable."""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as e:
            raise PermissionError(f"Cannot create directory {directory}: {e}")
    if not os.access(directory, os.W_OK):
        raise PermissionError(f"Directory not writable: {directory}")


def validate_rotation_confidence_threshold(threshold):
    """Validate rotation confidence threshold regardless of auto-detection flag."""
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"rotation_confidence_threshold must be between 0.0 and 1.0, got {threshold}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Banyan Extract - Document Processing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single PDF file
  python -m banyan_extract input.pdf output_dir/
 
  # Process all files in a directory
  python -m banyan_extract input_dir/ output_dir/ --is_input_dir
 
  # Use specific backend
  python -m banyan_extract input.pdf output_dir/ --backend nemoparse
 
  # Enable rotation detection
  python -m banyan_extract input.pdf output_dir/ --auto_detect_rotation
 
  # Manual rotation with bounding boxes
  python -m banyan_extract input.pdf output_dir/ --rotation_angle 90 --draw_bboxes
  
  # Process PPTX with default Nemotron OCR backend
  python -m banyan_extract presentation.pptx output_dir/
  
  # Process PPTX with Surya OCR backend
  python -m banyan_extract presentation.pptx output_dir/ --pptx_ocr_backend surya
        """
    )
    
    parser.add_argument("input_file", default=None, type=str, 
                       help="Path for a single file to be processed")
    parser.add_argument("output_dir", default=None, type=str, 
                       help="Path for output from single or multiple files")
    parser.add_argument("--is_input_dir", action="store_true", 
                       help="Flag to set input file to directory")
    parser.add_argument("--output_base", default="banyan-extract-output", type=str, 
                       help="Base name for output files (default: banyan-extract-output)")
    parser.add_argument("--backend", default="auto", type=str, 
                       help="Which backend to use: auto (auto-detect), nemoparse (Nemotron Parse), "
                            "marker (marker), pptx (PPTX processor). Default: auto")
    parser.add_argument("--config_file", default=".env", type=str, 
                       help="Which config file to use (defaults to ./.env)")
    parser.add_argument("--endpoint", default="", type=str, 
                       help="Endpoint URL for nemoretriever-parse model")
    parser.add_argument("--model_name", default="", type=str, 
                       help="Model name for nemoretriever-parse model")
    parser.add_argument("--checkpointing", action="store_true", 
                       help="If enabled, batch documents will be saved as they get processed")
    parser.add_argument("--draw_bboxes", action="store_true", default=False, 
                       help="If enabled, output will include images showing detected bounding boxes")
    parser.add_argument("--sort_by_position", action="store_true", default=True, 
                       help="Sort elements by spatial position for logical reading order (default: True)")
    
    # Updated Help Descriptions for re_run and temperature
    parser.add_argument("--re_run", action="store_true", default=False, help="Enables automatic retries. Uses contour area detection to evaluate missed regions, and re-runs the model at higher temperatures (max 3 retries) if the missed area is too high. Note: This flag is ONLY supported by the nemotron parse model.")
    parser.add_argument("--temperature", default=0.0, type=float, help="Temperature setting for the model. Note: This flag is ONLY supported by the nemotron parse model.")
    parser.add_argument("--rotation_angle", default=0, type=float, 
                       help="Angle in degrees to rotate the input page(s). Default: 0 (no rotation)")
    parser.add_argument("--auto_detect_rotation", action="store_true", 
                       help="Automatically detect and correct document rotation using Tesseract OCR")
    parser.add_argument("--rotation_confidence_threshold", default=0.7, type=float, 
                       help="Minimum confidence threshold (0.0-1.0) for automatic rotation detection. "
                            "Default: 0.7")
    
    # Add PPTX-specific arguments
    parser.add_argument("--pptx_ocr_backend", default="nemotron", type=str, 
                       help="OCR backend for PPTX processing: surya or nemotron. Default: nemotron")
    parser.add_argument("--pptx_nemotron_endpoint", default="", type=str, 
                       help="Nemotron endpoint URL for PPTX OCR (if using nemotron backend)")
    parser.add_argument("--pptx_nemotron_model", default="", type=str, 
                       help="Nemotron model name for PPTX OCR")
    
    args = parser.parse_args()
    
    # Early validation if user explicitly sets a backend that isn't nemoparse
    if args.backend not in ["auto", "nemoparse"]:
        if args.re_run or args.temperature != 0.0:
            parser.error("The --re_run and --temperature flags can only be used with the nemotron parse model (nemoparse backend).")
    
    # Validate rotation confidence threshold regardless of auto-detection flag
    try:
        validate_rotation_confidence_threshold(args.rotation_confidence_threshold)
    except ValueError as e:
        parser.error(str(e))
    
    # Validate PPTX OCR backend argument
    if args.pptx_ocr_backend not in ["surya", "nemotron"]:
        parser.error(f"Invalid PPTX OCR backend: {args.pptx_ocr_backend}. Must be 'surya' or 'nemotron'")
    
    # Warn if both manual rotation and auto detection are specified
    if args.auto_detect_rotation and args.rotation_angle != 0:
        logger.warning("Both manual rotation angle and auto rotation detection are specified. "
                      "Manual rotation will take precedence over auto detection.")
    
    # Check Tesseract dependencies if auto-detection is enabled
    if args.auto_detect_rotation:
        try:
            from banyan_extract.utils.tesseract_dependencies import has_tesseract_dependencies
            if not has_tesseract_dependencies():
                logger.warning("Auto-rotation detection enabled but Tesseract OCR dependencies are not available.")
                logger.warning("Rotation detection will be skipped. Install Tesseract OCR and pytesseract to enable this feature.")
        except ImportError:
            # If tesseract_dependencies module is not available, log a warning
            logger.warning("Auto-rotation detection enabled but dependency checking failed.")
            logger.warning("Ensure Tesseract OCR and pytesseract are installed for rotation detection.")
    
    return args


def main():
    args = parse_arguments()

    try:
        # Validate input file/directory
        if args.is_input_dir:
            if not os.path.isdir(args.input_file):
                raise NotADirectoryError(f"Input path is not a directory: {args.input_file}")
            validate_directory_writable(args.input_file)
            logger.info(f"Processing directory: {args.input_file}")
        else:
            validate_file_exists(args.input_file)
            logger.info(f"Processing file: {args.input_file}")

        # Validate output directory
        validate_directory_writable(args.output_dir)
        logger.info(f"Output directory: {args.output_dir}")

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

            # Validation for single file auto-detection
            if backend != "nemoparse" and (args.re_run or args.temperature != 0.0):
                raise ValueError(f"Error: The --re_run and --temperature flags are not supported for {backend} processing (detected from {filename}).")
                sys.exit(1)

        if args.is_input_dir:
            input_directory = args.input_file

            file_paths = []
            basenames = []
            for root, _, files in os.walk(input_directory):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    file_paths.append(filepath)
                    basenames.append(os.path.basename(filename))

            # For auto mode with directories, determine processor per file
            if backend == "auto":
                for filepath, basename in zip(file_paths, basenames):
                    try:
                        # Determine processor based on file extension
                        if filepath.lower().endswith('.pptx'):
                            if args.re_run or args.temperature != 0.0:
                                logger.warning("WARNING: The --re_run and --temperature flags are not supported for PPTX files. Cannot process {filepath}.", file=sys.stderr)
                                try:
                                    processor = PptxProcessor(
                                        ocr_backend=args.pptx_ocr_backend,
                                        nemotron_endpoint=args.pptx_nemotron_endpoint or args.endpoint,
                                        nemotron_model=args.pptx_nemotron_model or args.model_name
                                    )
                                except (NameError, ImportError) as e:
                                    logger.error(f"Failed to initialize PptxProcessor for file {filepath}: {e}")
                                    logger.warning("To enable PPTX functionality, install with: pip install python-pptx")
                                    if args.pptx_ocr_backend == "nemotron":
                                        logger.warning("For Nemotron OCR support, install with: pip install .[nemotronparse]")
                                    elif args.pptx_ocr_backend == "surya":
                                        logger.warning("For Surya OCR support, install with: pip install .[marker]")
                                    raise ImportError(f"PPTX processing dependencies are missing for file {filepath}") from e
                        else:  # Default to nemoparse for PDF and other files
                            if len(endpoint) == 0:
                                config_values = dotenv_values(args.config_file)
                                endpoint = config_values.get("NEMOPARSE_ENDPOINT")
                                model_name = config_values.get("NEMOPARSE_MODEL")
                            if endpoint != "":
                                processor = NemoparseProcessor(
                                    endpoint_url=endpoint, 
                                    model_name=model_name, 
                                    sort_by_position=args.sort_by_position
                                )
                            else:
                                raise ValueError("Missing nemotron-parse endpoint URL!")

                        # Process single file
                        output = processor.process_document(
                            filepath, 
                            re_run=args.re_run,
                            temperature=args.temperature,
                            rotation_angle=args.rotation_angle,
                            auto_detect_rotation=args.auto_detect_rotation,
                            rotation_confidence_threshold=args.rotation_confidence_threshold
                        )
                        if args.checkpointing:
                            output.save_output(output_directory, basename)
                    except Exception as e:
                        logger.error(f"Failed to process file {filepath}: {e}")
                        continue
            else:
                # Use the selected processor for all files
                try:
                    outputs = document_processor.process_batch_documents(
                        file_paths, 
                        use_checkpointing=args.checkpointing, 
                        draw_bboxes=args.draw_bboxes, 
                        output_dir=output_directory, 
                        re_run=args.re_run,
                        temperature=args.temperature,
                        rotation_angle=args.rotation_angle,
                        auto_detect_rotation=args.auto_detect_rotation,
                        rotation_confidence_threshold=args.rotation_confidence_threshold
                    )
                    if not args.checkpointing:
                        for file_output, basename in zip(outputs, basenames):
                            file_output.save_output(output_directory, basename)
                except Exception as e:
                    logger.error(f"Failed to process batch: {e}")
                    raise
        else:
            filename = args.input_file
            if filename.lower().endswith('.pptx'):
                backend = "pptx"
            elif filename.lower().endswith('.pdf'):
                backend = "nemoparse"
            else:
                backend = "nemoparse"  # Default to nemoparse for unknown types

            # Initialize the appropriate processor
            document_processor = None
            if backend == "nemoparse":
                if len(endpoint) == 0:
                    config_values = dotenv_values(args.config_file)
                    if not config_values:
                        raise ValueError(f"Config file {args.config_file} not found or empty")
                    endpoint = config_values.get("NEMOPARSE_ENDPOINT")
                    model_name = config_values.get("NEMOPARSE_MODEL")
                    if endpoint:
                        logger.info(f"Using endpoint: {endpoint}")
                    if model_name:
                        logger.info(f"Using model: {model_name}")

                if endpoint != "":
                    document_processor = NemoparseProcessor(
                        endpoint_url=endpoint, 
                        model_name=model_name, 
                        sort_by_position=args.sort_by_position
                    )
                else:
                    raise ValueError("Missing nemotron-parse endpoint URL!")
            elif backend == "marker":
                try:
                    document_processor = MarkerProcessor()
                except NameError as e:
                    logger.error("MarkerProcessor not available. Marker PDF processing requires additional dependencies.")
                    logger.warning("To enable marker functionality, install with: pip install .[marker]")
                    raise ImportError("MarkerProcessor not available. Install marker dependencies with: pip install .[marker]") from e
            elif backend == "pptx":
                try:
                    document_processor = PptxProcessor(
                        ocr_backend=args.pptx_ocr_backend,
                        nemotron_endpoint=args.pptx_nemotron_endpoint or args.endpoint,
                        nemotron_model=args.pptx_nemotron_model or args.model_name
                    )
                except NameError as e:
                    logger.error("PptxProcessor not available. PPTX processing requires additional dependencies.")
                    logger.warning("To enable PPTX functionality, install with: pip install python-pptx")
                    raise ImportError("PptxProcessor not available. Install pptx dependencies.") from e
                except ImportError as e:
                    logger.error("PPTX processing dependencies are missing or incomplete.")
                    logger.warning("To enable PPTX functionality, install with: pip install python-pptx")
                    if args.pptx_ocr_backend == "nemotron":
                        logger.warning("For Nemotron OCR support, install with: pip install .[nemotronparse]")
                    elif args.pptx_ocr_backend == "surya":
                        logger.warning("For Surya OCR support, install with: pip install .[marker]")
                    raise ImportError("PPTX processing dependencies are missing. Please install required packages.") from e
            else:
                raise ValueError(f"Unknown backend: {backend}")

            try:
                outputs = document_processor.process_document(
                    filename, 
                    re_run=args.re_run,
                    temperature=args.temperature,
                    rotation_angle=args.rotation_angle,
                    auto_detect_rotation=args.auto_detect_rotation,
                    rotation_confidence_threshold=args.rotation_confidence_threshold
                )
                outputs.save_output(output_directory, output_base)
            except Exception as e:
                logger.error(f"Failed to process document {filename}: {e}")
                raise

        logger.info("Processing completed successfully!")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
