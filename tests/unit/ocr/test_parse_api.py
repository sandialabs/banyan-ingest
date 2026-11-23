"""Exercise the multipart API through Banyan's public OCR and CLI entry points."""

import base64
import io
import sys

import httpx
from PIL import Image
import pymupdf
import pytest
from pptx import Presentation

from banyan_extract.banyan_extract import BanyanExtract
from banyan_extract.cli import main
from banyan_extract.ocr import NemotronOCR
from banyan_extract.processor.nemoparse_processor import NemoparseProcessor


HOSTED_ENDPOINT = "https://ai.api.nvidia.com/v1/retrieval/nvidia/nemotron-3.5-parse/parse"
CONTENT = "<x_0.1><y_0.2>Public example text<x_0.8><y_0.3><class_Text>"


@pytest.fixture
def parse_api(monkeypatch):
    """Record the real encoded request without opening a network connection."""
    requests = []
    result = {"content": CONTENT, "finish_reason": "stop"}

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=result)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(httpx, "post", client.post)
        yield requests, result


@pytest.mark.parametrize(("format_name", "mime_type"), [("JPEG", "jpeg"), ("TIFF", "png")])
def test_parse_preserves_bbox_data_and_uploads_a_supported_image(parse_api, format_name, mime_type):
    requests, _ = parse_api
    payload = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(payload, format=format_name)
    data_url = "data:image/png;base64," + base64.b64encode(payload.getvalue()).decode("ascii")
    ocr = NemotronOCR(HOSTED_ENDPOINT, api_key="test-key")

    assert ocr.get_detailed_ocr_results(data_url) == [{
        "type": "Text",
        "text": "Public example text",
        "bbox": {"xmin": 0.1, "ymin": 0.2, "xmax": 0.8, "ymax": 0.3},
    }]
    request, = requests
    assert request.method == "POST"
    assert str(request.url) == HOSTED_ENDPOINT
    assert request.headers["Authorization"] == "Bearer test-key"
    assert request.headers["Content-Type"].startswith("multipart/form-data; boundary=")
    assert b'name="document"' in request.content
    assert f"Content-Type: image/{mime_type}".encode() in request.content
    assert (payload.getvalue() if mime_type == "jpeg" else b"\x89PNG\r\n\x1a\n") in request.content
    assert b'"messages"' not in request.content


def test_local_parse_allows_blank_pages_and_raises_on_truncation(parse_api):
    requests, result = parse_api
    ocr = NemotronOCR("http://localhost:8000/v1/parse")
    image = Image.new("RGB", (32, 32), "white")
    result["content"] = ""
    assert ocr.ocr_image(image) == ""
    assert "Authorization" not in requests[0].headers

    result.update(content=CONTENT, finish_reason="length")
    with pytest.raises(ValueError, match="output token limit"):
        ocr.ocr_image(image)


def test_hosted_parse_requires_a_key(monkeypatch):
    monkeypatch.delenv("NEMOPARSE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="NEMOPARSE_API_KEY"):
        NemotronOCR(HOSTED_ENDPOINT)


@pytest.mark.parametrize("settings", [{"temperature": 0.4}, {"re_run": True}])
def test_parse_rejects_chat_sampling_without_uploading(parse_api, settings):
    requests, _ = parse_api
    processor = NemoparseProcessor(endpoint_url=HOSTED_ENDPOINT, api_key="test-key")
    with pytest.raises(ValueError, match="does not support --temperature or --re_run"):
        processor.process_document("unused.pdf", **settings)
    assert not requests


def make_pdf(path):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 75), "Public example text")
        pdf.save(path)


def test_cli_reads_hosted_config_and_decodes_pdf(tmp_path, monkeypatch, parse_api):
    requests, _ = parse_api
    monkeypatch.setenv("NEMOPARSE_API_KEY", "shell-key")
    config = tmp_path / "nemotron.config"
    config.write_text(f"NEMOPARSE_ENDPOINT={HOSTED_ENDPOINT}\nNEMOPARSE_API_KEY=file-key\n")
    pdf = tmp_path / "example.pdf"
    make_pdf(pdf)
    target = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", [
        "banyan-extract", str(pdf), str(target), "--config_file", str(config), "--save_bbox_data",
    ])

    main()

    request, = requests
    assert request.headers["Authorization"] == "Bearer shell-key"
    assert "Public example text" in (target / "banyan-extract-output.md").read_text()
    assert list(target.glob("*bbox.json"))


def test_directory_routes_pdf_and_pptx_pictures_to_parse_api(tmp_path, monkeypatch, parse_api):
    requests, _ = parse_api
    monkeypatch.delenv("NEMOPARSE_API_KEY", raising=False)
    config = tmp_path / "nemotron.config"
    config.write_text(f"NEMOPARSE_ENDPOINT={HOSTED_ENDPOINT}\nNEMOPARSE_API_KEY=file-key\n")
    source = tmp_path / "input"
    source.mkdir()
    make_pdf(source / "example.pdf")
    image = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(image, format="PNG")
    deck = Presentation()
    deck.slides.add_slide(deck.slide_layouts[6]).shapes.add_picture(image, 0, 0)
    deck.save(source / "example.pptx")

    output = tmp_path / "output"
    BanyanExtract(
        input_file=str(source), output_dir=str(output),
        config_file=str(config), is_input_dir=True,
    )()

    assert len(requests) == 2
    assert all(request.headers["Authorization"] == "Bearer file-key" for request in requests)
    assert "Public example text" in (output / "example.pptx.md").read_text()
