"""
Test cases for the evaluate extraction (contour detection) capabilities.
"""

import os
import re
import json
import pytest
from banyan_extract.processor.evaluate_extraction import evaluate_extraction

DATA_DIR_NO_BBOX = "tests/data/contour_detection/without_bbox"
DATA_DIR_WITH_BBOX = "tests/data/contour_detection/with_bbox"

def get_test_images_no_bbox():
    """Gathers images and expected percentages from the directory without bboxes."""
    test_cases = []
    if not os.path.exists(DATA_DIR_NO_BBOX):
        return test_cases
    for filename in os.listdir(DATA_DIR_NO_BBOX):
        if filename.endswith(".png"):
            match = re.search(r"(\d+)_percent\.png$", filename)
            if match:
                expected_pct = float(match.group(1))
                test_cases.append((filename, expected_pct))
    return test_cases

def get_test_images_with_bbox():
    """Gathers image/json pairs and expected percentages from the with_bbox directory."""
    test_cases = []
    if not os.path.exists(DATA_DIR_WITH_BBOX):
        return test_cases
    for filename in os.listdir(DATA_DIR_WITH_BBOX):
        if filename.endswith(".png"):
            # Matches '..._10_percent.png'
            match = re.search(r"(\d+)_percent\.png$", filename)
            if match:
                expected_pct = float(match.group(1))
                json_filename = filename.replace(".png", ".json")
                test_cases.append((filename, json_filename, expected_pct))
    return test_cases

@pytest.mark.parametrize("filename, expected_pct", get_test_images_no_bbox())
def test_evaluate_no_bbox(filename, expected_pct):
    """Validates logic for images where no bounding boxes are provided."""
    path = os.path.join(DATA_DIR_NO_BBOX, filename)
    with open(path, "rb") as f:
        img_bytes = f.read()

    should_rerun, missed_pct = evaluate_extraction(
        image_bytes=img_bytes,
        bbox_data=[],
        temperature=0.5,
        input_filename=filename
    )

    if 8.0 < expected_pct < 85.0:
        assert should_rerun
    else:
        assert not should_rerun

    assert missed_pct == pytest.approx(expected_pct, abs=5.0)

@pytest.mark.parametrize("img_file, json_file, expected_pct", get_test_images_with_bbox())
def test_evaluate_with_bbox(img_file, json_file, expected_pct):
    """Validates logic for images where bounding box JSON data is provided."""
    img_path = os.path.join(DATA_DIR_WITH_BBOX, img_file)
    json_path = os.path.join(DATA_DIR_WITH_BBOX, json_file)

    with open(img_path, "rb") as f:
        img_bytes = f.read()
    
    with open(json_path, "r") as f:
        bbox_data = json.load(f)

    should_rerun, missed_pct = evaluate_extraction(
        image_bytes=img_bytes,
        bbox_data=bbox_data,
        temperature=0.5,
        input_filename=img_file
    )

    # Reusing the same pass/fail boundary logic
    if 8.0 < expected_pct < 85.0:
        assert should_rerun
    else:
        assert not should_rerun

    # Percentage check with 5% tolerance
    assert missed_pct == pytest.approx(expected_pct, abs=5.0)