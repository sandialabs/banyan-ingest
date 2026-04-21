import cv2
import json
import os
import numpy as np


def apply_kmeans(image_bytes, num_clusters=2, input_filename="filtered_image", save_fig=False, output_dir=None):
    nparr = np.frombuffer(image_bytes, np.uint8)

    original_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image_rgb = cv2.cvtColor(original_img,cv2.COLOR_BGR2RGB)
    
    if original_img is None:
        print(f"[Evaluation] Failed to decode image: {input_filename}")

    pixel_values = image_rgb.reshape((-1,3))
    pixel_values = np.float32(pixel_values)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 0.2)

    #Apply the K-Means clustering
    retval, labels, centers = cv2.kmeans(pixel_values, num_clusters, None, criteria, 10, cv2.KMEANS_PP_CENTERS)

    #construct the segmented image from labels back to image dimensions
    segmented_data = centers[labels.flatten()].reshape(image_rgb.shape).astype(np.uint8)

    save_fig = True
    if save_fig:
        outpath = f"{input_filename}_segmented.png"
        if output_dir is not None:
            outpath = f"{output_dir}/{outpath}"
        cv2.imwrite(outpath, segmented_data)

    #return segmented_data
    success, encoded_img = cv2.imencode(".png", cv2.cvtColor(segmented_data, cv2.COLOR_RGB2BGR))
    if not success:
        raise ValueError("Failed to encode image")

    image_bytes = encoded_img.tobytes()
    return image_bytes
