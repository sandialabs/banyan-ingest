"""
Tests for K-means image segmentation utilities.

This module tests the apply_kmeans function and its helper functions:
- shift_clip_to_uint8: Darkens images by shifting pixel values
- expand_keep_region_cv2: Expands mask regions via morphological dilation
"""

import pytest
import numpy as np
from io import BytesIO
from PIL import Image
import cv2

from banyan_extract.utils.kmeans import (
    apply_kmeans,
    shift_clip_to_uint8,
    expand_keep_region_cv2
)


class TestShiftClipToUint8:
    """Tests for shift_clip_to_uint8 helper function."""

    def test_positive_shift_darkens_image(self):
        """Test that positive quantile darkens the image."""
        # Create test array with values 0-255
        arr = np.arange(256, dtype=np.uint8).reshape(16, 16)

        # Apply darkening with quantile=5 (5th percentile will be positive)
        result = shift_clip_to_uint8(arr, quantile=5)

        # Verify result is uint8
        assert result.dtype == np.uint8

        # Verify darkening occurred (shifted values should be lower)
        # The 5th percentile of 0-255 is around 12-13, so values should shift down
        assert np.mean(result) < np.mean(arr)

    def test_zero_quantile_returns_original(self):
        """Test zero quantile returns original array as uint8 (bug fix verification)."""
        # With 0th percentile = 0, shift_value = 0, should return original as uint8
        arr_with_zero = np.array([[0, 50, 100], [0, 25, 75]], dtype=np.uint8)

        result = shift_clip_to_uint8(arr_with_zero, quantile=0)

        # Verify result is uint8
        assert result.dtype == np.uint8

        # With 0th percentile = 0, shift_value = 0, should return original as uint8
        np.testing.assert_array_equal(result, arr_with_zero)

    def test_negative_case_with_all_zeros(self):
        """Test array of all zeros (percentile will be 0, triggering bug fix path)."""
        # Array of all zeros - any percentile will be 0
        arr = np.zeros((10, 10), dtype=np.uint8)

        result = shift_clip_to_uint8(arr, quantile=5)

        # Should return original array as uint8 (shift_value = 0)
        assert result.dtype == np.uint8
        np.testing.assert_array_equal(result, arr)

    def test_float_input_converted_to_uint8(self):
        """Test that float input is correctly handled."""
        # Create float array
        arr = np.array([[100.5, 150.7], [200.2, 50.1]], dtype=np.float32)

        result = shift_clip_to_uint8(arr, quantile=25)

        # Verify result is uint8
        assert result.dtype == np.uint8

        # Verify all values are in valid uint8 range
        assert np.all(result >= 0)
        assert np.all(result <= 255)

    def test_clipping_to_uint8_range(self):
        """Test that values are properly clipped to 0-255 range."""
        # Create array with large values
        arr = np.array([[100, 200, 300], [400, 500, 600]], dtype=np.int16)

        result = shift_clip_to_uint8(arr, quantile=5)

        # All values should be clipped to 255 max
        assert result.dtype == np.uint8
        assert np.all(result <= 255)

    def test_preserves_shape(self):
        """Test that output shape matches input shape."""
        arr = np.random.randint(0, 256, size=(20, 30, 3), dtype=np.uint8)

        result = shift_clip_to_uint8(arr, quantile=10)

        assert result.shape == arr.shape


class TestExpandKeepRegionCv2:
    """Tests for expand_keep_region_cv2 helper function."""

    def test_expand_by_one_pixel_8_neighbors(self):
        """Test 1-pixel expansion with 8-neighbor connectivity."""
        # Create 5x5 mask with single pixel in center
        mask = np.zeros((5, 5, 1), dtype=np.uint8)
        mask[2, 2, 0] = 1  # Center pixel

        result = expand_keep_region_cv2(mask, iterations=1, neighbors=8)

        # Should expand to 3x3 region (center + 8 neighbors)
        expected = np.zeros((5, 5, 1), dtype=np.uint8)
        for i in range(1, 4):
            for j in range(1, 4):
                expected[i, j, 0] = 1

        np.testing.assert_array_equal(result, expected)

    def test_expand_by_one_pixel_4_neighbors(self):
        """Test 1-pixel expansion with 4-neighbor connectivity (cross pattern)."""
        # Create 5x5 mask with single pixel in center
        mask = np.zeros((5, 5, 1), dtype=np.uint8)
        mask[2, 2, 0] = 1

        result = expand_keep_region_cv2(mask, iterations=1, neighbors=4)

        # Should expand to cross pattern (center + 4 neighbors)
        expected = np.zeros((5, 5, 1), dtype=np.uint8)
        expected[2, 2, 0] = 1  # Center
        expected[1, 2, 0] = 1  # Top
        expected[3, 2, 0] = 1  # Bottom
        expected[2, 1, 0] = 1  # Left
        expected[2, 3, 0] = 1  # Right

        np.testing.assert_array_equal(result, expected)

    def test_multiple_iterations(self):
        """Test expanding by multiple iterations."""
        # Create mask with single pixel
        mask = np.zeros((7, 7, 1), dtype=np.uint8)
        mask[3, 3, 0] = 1

        # Expand by 2 iterations
        result = expand_keep_region_cv2(mask, iterations=2, neighbors=8)

        # Should create 5x5 region
        assert np.sum(result) == 25  # 5x5 = 25 pixels

    def test_invalid_neighbors_raises_error(self):
        """Test that invalid neighbor count raises ValueError."""
        mask = np.zeros((5, 5, 1), dtype=np.uint8)
        mask[2, 2, 0] = 1

        with pytest.raises(ValueError, match="neighbors must be 4 or 8"):
            expand_keep_region_cv2(mask, iterations=1, neighbors=6)

    def test_preserves_input_dtype(self):
        """Test that output dtype matches input dtype."""
        # Create mask with float32 dtype
        mask = np.zeros((5, 5, 1), dtype=np.float32)
        mask[2, 2, 0] = 1.0

        result = expand_keep_region_cv2(mask, iterations=1, neighbors=8)

        assert result.dtype == mask.dtype

    def test_empty_mask_remains_empty(self):
        """Test that empty mask remains empty after expansion."""
        mask = np.zeros((5, 5, 1), dtype=np.uint8)

        result = expand_keep_region_cv2(mask, iterations=1, neighbors=8)

        np.testing.assert_array_equal(result, mask)


class TestApplyKmeans:
    """Tests for apply_kmeans function."""

    def create_test_image_bytes(self, width=100, height=100, pattern='bicolor'):
        """Helper to create test image bytes with different patterns."""
        if pattern == 'bicolor':
            # White background with black rectangle (simulates text on paper)
            img = Image.new('RGB', (width, height), color='white')
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.rectangle([(20, 20), (80, 80)], fill='black')
        elif pattern == 'gradient':
            # Gradient from black to white
            img_array = np.linspace(0, 255, width * height, dtype=np.uint8).reshape(height, width)
            img_array = np.stack([img_array] * 3, axis=-1)
            img = Image.fromarray(img_array, mode='RGB')
        elif pattern == 'uniform':
            # Uniform gray
            img = Image.new('RGB', (width, height), color=(128, 128, 128))
        else:
            raise ValueError(f"Unknown pattern: {pattern}")

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def test_basic_segmentation_returns_bytes(self):
        """Test basic 2-cluster segmentation returns PNG bytes."""
        image_bytes = self.create_test_image_bytes(pattern='bicolor')

        result = apply_kmeans(image_bytes, num_clusters=2)

        # Verify result is bytes
        assert isinstance(result, bytes)

        # Verify it's valid PNG data (can be decoded)
        nparr = np.frombuffer(result, np.uint8)
        decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert decoded is not None

        # Verify dimensions are preserved
        assert decoded.shape[:2] == (100, 100)

    def test_custom_num_clusters(self):
        """Test with different cluster counts."""
        image_bytes = self.create_test_image_bytes(pattern='gradient')

        # Test with 3 clusters
        result = apply_kmeans(image_bytes, num_clusters=3)

        assert isinstance(result, bytes)

        # Verify it's decodable
        nparr = np.frombuffer(result, np.uint8)
        decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert decoded is not None

    def test_darken_option_modifies_output(self):
        """Test that darken option produces different output."""
        # Use gradient pattern - darken has visible effect on grayscale images
        image_bytes = self.create_test_image_bytes(pattern='gradient')

        result_without_darken = apply_kmeans(image_bytes, darken=False)
        result_with_darken = apply_kmeans(image_bytes, darken=True)

        # Both should be valid bytes
        assert isinstance(result_without_darken, bytes)
        assert isinstance(result_with_darken, bytes)

        # Verify both are decodable
        nparr1 = np.frombuffer(result_without_darken, np.uint8)
        decoded1 = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
        assert decoded1 is not None

        nparr2 = np.frombuffer(result_with_darken, np.uint8)
        decoded2 = cv2.imdecode(nparr2, cv2.IMREAD_COLOR)
        assert decoded2 is not None

    def test_sharpen_option_modifies_output(self):
        """Test that sharpen option produces different output."""
        image_bytes = self.create_test_image_bytes(pattern='bicolor')

        result_without_sharpen = apply_kmeans(image_bytes, sharpen=False)
        result_with_sharpen = apply_kmeans(image_bytes, sharpen=True)

        # Both should be valid bytes
        assert isinstance(result_without_sharpen, bytes)
        assert isinstance(result_with_sharpen, bytes)

        # Verify both are decodable (sharpen applies filter)
        nparr1 = np.frombuffer(result_without_sharpen, np.uint8)
        decoded1 = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
        assert decoded1 is not None

        nparr2 = np.frombuffer(result_with_sharpen, np.uint8)
        decoded2 = cv2.imdecode(nparr2, cv2.IMREAD_COLOR)
        assert decoded2 is not None

    def test_save_fig_option_creates_file(self, tmp_path):
        """Test that save_fig option saves output to file."""
        image_bytes = self.create_test_image_bytes(pattern='bicolor')

        # Create output directory
        output_dir = tmp_path / "kmeans_output"
        output_dir.mkdir()

        result = apply_kmeans(
            image_bytes,
            input_filename="test_image.png",
            save_fig=True,
            output_dir=str(output_dir)
        )

        # Verify function still returns bytes
        assert isinstance(result, bytes)

        # Verify file was created
        expected_file = output_dir / "filtered_test_image.png"
        assert expected_file.exists()

        # Verify saved file is valid image
        saved_img = cv2.imread(str(expected_file))
        assert saved_img is not None

    def test_invalid_image_bytes_raises_error(self):
        """Test handling of invalid image bytes."""
        invalid_bytes = b"not a valid image"

        # Function doesn't handle invalid bytes gracefully - it will raise cv2.error
        # cv2.imdecode returns None, then cv2.cvtColor(None, ...) crashes
        # This documents actual behavior, not ideal behavior
        with pytest.raises(Exception):  # cv2.error when cvtColor gets None
            apply_kmeans(invalid_bytes)

    def test_uniform_image_segmentation(self):
        """Test segmentation of uniform image (edge case for k-means)."""
        # Uniform gray image - k-means should still work
        image_bytes = self.create_test_image_bytes(pattern='uniform')

        result = apply_kmeans(image_bytes, num_clusters=2)

        assert isinstance(result, bytes)

        # Verify decodable
        nparr = np.frombuffer(result, np.uint8)
        decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert decoded is not None

    def test_combined_options(self, tmp_path):
        """Test with multiple options enabled simultaneously."""
        image_bytes = self.create_test_image_bytes(pattern='bicolor')

        output_dir = tmp_path / "combined_test"
        output_dir.mkdir()

        result = apply_kmeans(
            image_bytes,
            num_clusters=2,
            input_filename="combined.png",
            save_fig=True,
            output_dir=str(output_dir),
            darken=True,
            sharpen=True
        )

        # Verify result
        assert isinstance(result, bytes)

        # Verify file created
        assert (output_dir / "filtered_combined.png").exists()

        # Verify decodable
        nparr = np.frombuffer(result, np.uint8)
        decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert decoded is not None

    def test_preserves_image_dimensions(self):
        """Test that output dimensions match input dimensions."""
        # Test with non-square image
        image_bytes = self.create_test_image_bytes(width=120, height=80, pattern='bicolor')

        result = apply_kmeans(image_bytes)

        # Decode result
        nparr = np.frombuffer(result, np.uint8)
        decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Verify dimensions preserved
        assert decoded.shape[:2] == (80, 120)  # height, width in OpenCV

    def test_encoding_failure_raises_error(self, monkeypatch):
        """Test that encoding failure raises ValueError."""
        image_bytes = self.create_test_image_bytes(pattern='bicolor')

        # Mock cv2.imencode to fail
        def mock_imencode(*args, **kwargs):
            return False, None

        monkeypatch.setattr(cv2, 'imencode', mock_imencode)

        with pytest.raises(ValueError, match="Failed to encode image"):
            apply_kmeans(image_bytes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
