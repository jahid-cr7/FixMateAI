"""Tests for screenshot validation and OpenCV preprocessing."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image, ImageDraw

from src.image_processing import (
    MAX_IMAGE_BYTES,
    ImageValidationError,
    apply_threshold,
    increase_contrast,
    preprocess_image,
    reduce_noise,
    to_grayscale,
    validate_image,
)


def _generated_image_bytes(image_format: str = "PNG") -> bytes:
    """Create a small in-memory image; no fixture file is required."""
    image = Image.new("RGB", (320, 100), "white")
    ImageDraw.Draw(image).text((10, 35), "Error: file not found", fill="black")
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


@pytest.mark.parametrize("image_format", ["PNG", "JPEG"])
def test_validate_generated_supported_images(image_format: str) -> None:
    """Actual decoded PNG and JPEG content should pass validation."""
    validated = validate_image(_generated_image_bytes(image_format))
    assert validated.image_format == image_format
    assert validated.image.size == (320, 100)


def test_invalid_file_content_is_rejected() -> None:
    """A filename-independent non-image payload must be rejected."""
    with pytest.raises(ImageValidationError, match="not a valid"):
        validate_image(b"this is not image content")


def test_oversized_file_is_rejected_before_decoding() -> None:
    """Uploads over 5 MB should fail with a helpful size message."""
    with pytest.raises(ImageValidationError, match="5 MB"):
        validate_image(b"x" * (MAX_IMAGE_BYTES + 1))


def test_preprocessing_pipeline_uses_generated_image() -> None:
    """The full pipeline should return a thresholded grayscale array."""
    validated = validate_image(_generated_image_bytes())
    processed = preprocess_image(validated.image, use_threshold=True)
    assert processed.shape == (100, 320)
    assert processed.dtype == np.uint8
    assert set(np.unique(processed)).issubset({0, 255})


def test_preprocessing_steps_are_independently_callable() -> None:
    """Each OpenCV stage should accept and return testable arrays."""
    rgb = np.full((40, 60, 3), 180, dtype=np.uint8)
    rgb[10:30, 20:40] = 20
    grayscale = to_grayscale(rgb)
    contrasted = increase_contrast(grayscale)
    denoised = reduce_noise(contrasted)
    thresholded = apply_threshold(denoised)
    assert grayscale.ndim == contrasted.ndim == denoised.ndim == thresholded.ndim == 2
    assert thresholded.shape == grayscale.shape

