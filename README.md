# Banyan Ingest

`banyan_ingest` is a python module that prepares documents for use in GenAI and LLM applications. 

Rather than re-invent the wheel, `banyan_ingest` aims to utilize state-of-the-art tools to provide this capability. 


## Installation

In a python environment (`conda`, `venv`, etc.), use the following:

```
cd PATH_TO_REPO/
pip install .
```

You will also need to make sure `poppler` is installed on your system.

## Supported Tools and File Formats
Currently we provide support for `marker` ([link here](https://github.com/datalab-to/marker)) and NVIDIA's `nemotron-parse` models ([link here](https://build.nvidia.com/nvidia/nemotron-parse)).
To install the necessary dependencies for these tools please use `pip install .[marker]` or `pip install .[nemotronparse]` respectively.

Note: please ensure you follow the guidelines and usage licenses of the tools.

## Examples
The `example_XXX.py` scripts contain basic scripts for processing pdf documents using different OCR tools under the hood.
