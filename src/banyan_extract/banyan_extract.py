import os
import sys
import logging

import argparse

from dotenv import load_dotenv, dotenv_values

from pathlib import Path

from banyan_extract.utils import gather_files
from banyan_extract.utils.logging_config import setup_logger

from banyan_extract import NemoparseProcessor

try:
    from banyan_extract.processor import MarkerProcessor
except ImportError:
    pass

try:
    from banyan_extract.processor import PptxProcessor
except ImportError:
    pass


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


class BanyanExtract:
    # Default configs [Note: descriptions provided in 'cli.py' file]
    default_config = dict()
    default_config["input_file"] = None
    default_config["output_dir"] = None
    default_config["is_input_dir"] = False
    default_config["output_base"] = "banyan-extract-output"
    default_config["backend"] = "auto"
    default_config["config_file"] = ".env"
    default_config["endpoint"] = ""
    default_config["model_name"] = ""
    default_config["checkpointing"] = False
    default_config["draw_bboxes"] = False
    default_config["sort_by_position"] = True
    default_config["overwrite"] = False

    # Updated Help Descriptions for re_run and temperature
    default_config["re_run"] = False 
    default_config["temperature"] = 0.0 

    # Rotation detection arguments
    default_config["rotation_angle"] = 0
    default_config["auto_detect_rotation"] = False
    default_config["rotation_confidence_threshold"] = 0.7

    # Contrast filter arguments
    default_config["apply_contrast_filter"] = False 
    
    # Add PPTX-specific arguments
    default_config["pptx_ocr_backend"] = "nemotron"
    default_config["pptx_nemotron_endpoint"] = ""
    default_config["pptx_nemotron_model"] = ""
    
    valid_kwargs = set(default_config.keys())

    # Default configs for "__call__" method  (block changing endpoint for now)
    valid_call_kwargs = valid_kwargs.copy()
    valid_call_kwargs.remove("backend")
    valid_call_kwargs.remove("config_file")
    valid_call_kwargs.remove("endpoint")
    valid_call_kwargs.remove("model_name")
    valid_call_kwargs.remove("pptx_ocr_backend")
    valid_call_kwargs.remove("pptx_nemotron_endpoint")
    valid_call_kwargs.remove("pptx_nemotron_model")

    default_call_config = dict()    
    for key in valid_call_kwargs:
        default_call_config[key] = default_config[key]


    def __init__(self, logger=None, **kwargs):
        # Override default settings with values passed as keyword arguments
        config = {
            **self.default_config,
            **kwargs,
        }

        # Assign each config entry as an instance attribute
        for key, value in config.items():
            setattr(self, key, value)

        self.logger = logger

        self.validate_settings()


    def validate_settings(self):
        
        # Validate input file/directory
        if self.is_input_dir:
            if not os.path.isdir(self.input_file):
                raise NotADirectoryError(f"Input path is not a directory: {self.input_file}")
            validate_directory_writable(self.input_file)
            self.logger.info(f"Processing directory: {self.input_file}")
        else:
            validate_file_exists(self.input_file)
            self.logger.info(f"Processing file: {self.input_file}")
    
        # Validate output directory
        validate_directory_writable(self.output_dir)
        self.logger.info(f"Output directory: {self.output_dir}")


    def get_call_config(self):
        call_config = dict()
        for key in self.valid_call_kwargs:
            call_config[key] = getattr(self, key, None)
        return call_config

    def __call__(self, **kwargs):

        # Check if settings require re-validation
        should_revalidate = False
        require_revalidation_keys = ["input_file", "is_input_dir", "output_dir"]
        for key in require_revalidation_keys:
            if (key in kwargs) and (kwargs[key] != getattr(self, key)):
                should_revalidate = True
                break

        # Override default settings with values passed as keyword arguments
        previous_call_config = self.get_call_config()
        call_config = {
            **previous_call_config,
            **kwargs,
        }

        # Assign each config entry as an instance attribute
        for key, value in call_config.items():
            setattr(self, key, value)

        # Re-validate settings if needed
        if should_revalidate:
            self.validate_settings()

        output_directory = self.output_dir
        output_base = self.output_base
        endpoint = self.endpoint
        model_name = self.model_name
        backend = self.backend
    
        # Auto-detect backend based on file extension if backend is "auto"
        if self.backend == "auto":
            if self.is_input_dir:
                # For directories, we'll determine processor per file
                backend = "auto"
            else:
                # For single files, detect based on extension
                filename = self.input_file
                if filename.lower().endswith('.pptx'):
                    backend = "pptx"
                elif filename.lower().endswith('.pdf'):
                    backend = "nemoparse"
                else:
                    backend = "nemoparse"  # Default to nemoparse for unknown types
    
                # Validation for single file auto-detection
                if backend != "nemoparse" and (self.re_run or self.temperature != 0.0):
                    raise ValueError(f"Error: The --re_run and --temperature flags are not supported for {backend} processing (detected from {filename}).")
    
        if len(endpoint) == 0:
            if os.path.exists(self.config_file):
                config_values = dotenv_values(self.config_file)
            else:
                config_values = dict()
                config_values["NEMOPARSE_ENDPOINT"] = os.getenv("NEMOPARSE_ENDPOINT")
                config_values["NEMOPARSE_MODEL"] = os.getenv("NEMOPARSE_MODEL")
    
            if not config_values or config_values["NEMOPARSE_ENDPOINT"] is None or config_values["NEMOPARSE_MODEL"] is None:
                raise ValueError(f"Config file {self.config_file} not found or empty and environment variables (NEMOPARSE_ENDPOINT and NEMOPARSE_MODEL) not set")
    
            endpoint = config_values.get("NEMOPARSE_ENDPOINT")
            model_name = config_values.get("NEMOPARSE_MODEL")
            if endpoint:
                self.logger.info(f"Using endpoint: {endpoint}")
            if model_name:
                self.logger.info(f"Using model: {model_name}")

        # Initialize the appropriate processor
        document_processor = None
        if backend == "nemoparse":
            if endpoint != "":
                document_processor = NemoparseProcessor(
                    endpoint_url=endpoint, 
                    model_name=model_name, 
                    sort_by_position=self.sort_by_position,
                    output_dir=output_directory
                )
            else:
                raise ValueError("Missing nemotron-parse endpoint URL!")
        elif backend == "marker":
            try:
                document_processor = MarkerProcessor(output_dir=output_directory)
            except NameError as e:
                self.logger.error("MarkerProcessor not available. Marker PDF processing requires additional dependencies.")
                self.logger.warning("To enable marker functionality, install with: pip install .[marker]")
                raise ImportError("MarkerProcessor not available. Install marker dependencies with: pip install .[marker]") from e
        elif backend == "pptx":
            try:
                document_processor = PptxProcessor(
                    ocr_backend=self.pptx_ocr_backend,
                    nemotron_endpoint=self.pptx_nemotron_endpoint or self.endpoint,
                    nemotron_model=self.pptx_nemotron_model or self.model_name,
                    output_dir=output_directory,
                )
            except NameError as e:
                self.logger.error("PptxProcessor not available. PPTX processing requires additional dependencies.")
                self.logger.warning("To enable PPTX functionality, install with: pip install python-pptx")
                raise ImportError("PptxProcessor not available. Install pptx dependencies.") from e
            except ImportError as e:
                self.logger.error("PPTX processing dependencies are missing or incomplete.")
                self.logger.warning("To enable PPTX functionality, install with: pip install python-pptx")
                if self.pptx_ocr_backend == "nemotron":
                    self.logger.warning("For Nemotron OCR support, install with: pip install .[nemotronparse]")
                elif self.pptx_ocr_backend == "surya":
                    self.logger.warning("For Surya OCR support, install with: pip install .[marker]")
                raise ImportError("PPTX processing dependencies are missing. Please install required packages.") from e
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
        if not os.path.exists(output_directory):
            print(f"Output directory does not exsist, creating {output_directory}")
            os.mkdirs(output_directory)
    
        if self.is_input_dir:
            input_directory = self.input_file
    
            file_paths_relative = gather_files(Path(input_directory), self.effective_extensions, max_depth=self.recursion_depth)
            file_paths = [str(Path(input_directory) / p) for p in file_paths_relative]
            basenames = [p.name for p in file_paths_relative]
    
            # For auto mode with directories, determine processor per file
            if backend == "auto":
                for filepath, basename in zip(file_paths, basenames):
                    try:
                        # Determine processor based on file extension
                        if filepath.lower().endswith('.pptx'):
                            if self.re_run or self.temperature != 0.0:
                                self.logger.warning("WARNING: The --re_run and --temperature flags are not supported for PPTX files. Cannot process {filepath}.", file=sys.stderr)
                                try:
                                    processor = PptxProcessor(
                                        ocr_backend=self.pptx_ocr_backend,
                                        nemotron_endpoint=self.pptx_nemotron_endpoint or self.endpoint,
                                        nemotron_model=self.pptx_nemotron_model or self.model_name,
                                        output_dir=output_directory,
                                    )
                                except (NameError, ImportError) as e:
                                    self.logger.error(f"Failed to initialize PptxProcessor for file {filepath}: {e}")
                                    self.logger.warning("To enable PPTX functionality, install with: pip install python-pptx")
                                    if self.pptx_ocr_backend == "nemotron":
                                        self.logger.warning("For Nemotron OCR support, install with: pip install .[nemotronparse]")
                                    elif self.pptx_ocr_backend == "surya":
                                        self.logger.warning("For Surya OCR support, install with: pip install .[marker]")
                                    raise ImportError(f"PPTX processing dependencies are missing for file {filepath}") from e
                        else:  # Default to nemoparse for PDF and other files
                            if endpoint != "":
                                processor = NemoparseProcessor(
                                    endpoint_url=endpoint, 
                                    model_name=model_name, 
                                    sort_by_position=self.sort_by_position,
                                    output_dir=output_directory,
                                )
                            else:
                                raise ValueError("Missing nemotron-parse endpoint URL!")
                            
                        # Process single file
                        output = processor.process_document(
                            filepath,
                            output_dir=output_directory, 
                            draw_bboxes=self.draw_bboxes,
                            re_run=self.re_run,
                            temperature=self.temperature,
                            rotation_angle=self.rotation_angle,
                            auto_detect_rotation=self.auto_detect_rotation,
                            rotation_confidence_threshold=self.rotation_confidence_threshold,
                            apply_highcontrast_filter=self.apply_contrast_filter,
                            overwrite=self.overwrite,
                            output_basename=basename,
                        )

                        if output is not None:
                            output.save_output(output_directory, basename)
                            
                    except Exception as e:
                        self.logger.error(f"Failed to process file {filepath}: {e}")
                        continue
            else:
                # Use the selected processor for all files
                try:
                    outputs = document_processor.process_batch_documents(
                        file_paths, 
                        output_dir=output_directory, 
                        use_checkpointing=self.checkpointing, 
                        draw_bboxes=self.draw_bboxes,
                        re_run=self.re_run,
                        temperature=self.temperature,
                        rotation_angle=self.rotation_angle,
                        auto_detect_rotation=self.auto_detect_rotation,
                        rotation_confidence_threshold=self.rotation_confidence_threshold,
                        apply_highcontrast_filter=self.apply_contrast_filter,
                        overwrite=self.overwrite,
                        output_basenames=basenames,
                    )
                    for file_output, basename in zip(outputs, basenames):
                        if file_output is not None:
                            file_output.save_output(output_directory, basename)
                except Exception as e:
                    self.logger.error(f"Failed to process batch: {e}")
                    raise
        else:
            try:
                outputs = document_processor.process_document(
                    filename, 
                    draw_bboxes=self.draw_bboxes,
                    re_run=self.re_run,
                    temperature=self.temperature,
                    rotation_angle=self.rotation_angle,
                    auto_detect_rotation=self.auto_detect_rotation,
                    rotation_confidence_threshold=self.rotation_confidence_threshold,
                    apply_highcontrast_filter=self.apply_contrast_filter,
                    overwrite=self.overwrite,
                    output_basename=output_base,
                )
                if outputs is not None:
                    outputs.save_output(output_directory, output_base)
            except Exception as e:
                self.logger.error(f"Failed to process document {filename}: {e}")
                raise
    
        self.logger.info("Processing completed successfully!")
