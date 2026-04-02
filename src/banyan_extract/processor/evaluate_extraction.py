import cv2
import json
import os
import numpy as np

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _expand_and_clip_box(xmin, ymin, xmax, ymax, pad_x, pad_y, w, h):
    xmin = _clamp(xmin - pad_x, 0, w - 1)
    ymin = _clamp(ymin - pad_y, 0, h - 1)
    xmax = _clamp(xmax + pad_x, 0, w - 1)
    ymax = _clamp(ymax + pad_y, 0, h - 1)
    return xmin, ymin, xmax, ymax

def evaluate_extraction(
    image_bytes,
    bbox_data,
    temperature,
    input_filename="image",
    min_threshold=8.0,
    max_threshold=85.0,
    save_fig=False,
    output_dir=None,
    padding_x=150,
    padding_y=150,
    dilate_kernel_size=(13, 13),
    dilate_iterations=3
):
    """
    Evaluates a single image and its bounding box data to determine if it needs to be re-run.
    Returns a tuple (should_rerun: bool, missed_percentage: float)
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    original_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if original_img is None:
        print(f"[Evaluation] Failed to decode image: {input_filename}")
        return False, 0.0

    h, w = original_img.shape[:2]
    total_image_area = h * w

    if total_image_area == 0:
        print(f"[Evaluation] Image has zero area: {input_filename}")
        return False, 0.0

    gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
    _, binary_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, dilate_kernel_size)
    erased_mask = cv2.dilate(binary_mask, kernel, iterations=dilate_iterations)

    display_img = None
    bbox_img = None
    if save_fig:
        display_img = original_img.copy()
        bbox_img = original_img.copy()

    for item in bbox_data:
        bbox = item.get("bbox")
        if not bbox:
            continue

        x_min = int(bbox.get("xmin", 0) * w)
        y_min = int(bbox.get("ymin", 0) * h)
        x_max = int(bbox.get("xmax", 0) * w)
        y_max = int(bbox.get("ymax", 0) * h)

        x1, x2 = sorted([x_min, x_max])
        y1, y2 = sorted([y_min, y_max])

        px1, py1, px2, py2 = _expand_and_clip_box(x1, y1, x2, y2, padding_x, padding_y, w, h)

        cv2.rectangle(erased_mask, (px1, py1), (px2, py2), 0, -1)

        if save_fig:
            cv2.rectangle(display_img, (px1, py1), (px2, py2), (255, 255, 255), -1)
            cv2.rectangle(bbox_img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.rectangle(bbox_img, (px1, py1), (px2, py2), (0, 255, 0), 2)

    contours, _ = cv2.findContours(erased_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    total_missed_area = 0.0
    for cnt in contours:
        total_missed_area += cv2.contourArea(cnt)

    if save_fig:
        overlay = display_img.copy()
        cv2.drawContours(overlay, contours, -1, (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.4, display_img, 0.6, 0, display_img)

    missed_percentage = (total_missed_area / total_image_area) * 100
    should_rerun = min_threshold < missed_percentage < max_threshold

    # Cleaned up print logic that only reports the facts
    print(f"\n=== Evaluation Results for {input_filename} (Temp: {temperature}) ===")
    if should_rerun:
        print("Coverage: Poor")
        print(f"Details: Bounding boxes missed {missed_percentage:.1f}% of the detected visual content.")
    elif missed_percentage <= min_threshold:
        print("Coverage: Sufficient")
        print(f"Details: Captured nearly all detected content (Missed: {missed_percentage:.1f}%).")
    else:
        print("Coverage: Complex Image")
        print(f"Details: Missed {missed_percentage:.1f}%. Binary contour detection unreliable for this image type.")
    print("==================================================\n")

    if save_fig and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        name_without_ext = os.path.splitext(input_filename)[0]
        
        display_out_path = os.path.join(output_dir, f"{name_without_ext}_temp{temperature}_highlight.png")
        bbox_out_path = os.path.join(output_dir, f"{name_without_ext}_temp{temperature}_bboxes.png")
        
        cv2.imwrite(display_out_path, display_img)
        cv2.imwrite(bbox_out_path, bbox_img)

    return should_rerun, missed_percentage