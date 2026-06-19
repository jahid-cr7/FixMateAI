"""Validation and OCR-oriented preprocessing for uploaded screenshots."""

from __future__ import annotations

import io
import warnings
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG"}


class ImageValidationError(ValueError):
    """Raised when uploaded bytes are not a supported, safe image."""


@dataclass(frozen=True)
class ValidatedImage:
    """A decoded image and trusted metadata derived from its content."""

    image: Image.Image
    image_format: str
    width: int
    height: int


def validate_image(image_bytes: bytes) -> ValidatedImage:
    """Validate size and decoded content for a PNG or JPEG upload."""
    if not image_bytes:
        raise ImageValidationError("The uploaded file is empty.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ImageValidationError("The image is larger than the 5 MB limit.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as candidate:
                image_format = (candidate.format or "").upper()
                candidate.verify()
            with Image.open(io.BytesIO(image_bytes)) as decoded:
                decoded.load()
                image = decoded.convert("RGB").copy()
    except Image.DecompressionBombWarning as error:
        raise ImageValidationError("The image dimensions are too large to process safely.") from error
    except Image.DecompressionBombError as error:
        raise ImageValidationError("The image dimensions are too large to process safely.") from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise ImageValidationError(
            "The file is not a valid, readable PNG or JPEG image."
        ) from error

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ImageValidationError("Only PNG, JPG, and JPEG image content is supported.")
    if image.width < 1 or image.height < 1:
        raise ImageValidationError("The image has invalid dimensions.")

    return ValidatedImage(image, image_format, image.width, image.height)


def pil_to_rgb_array(image: Image.Image) -> np.ndarray:
    """Convert a Pillow image to an OpenCV-compatible RGB array."""
    return np.asarray(image.convert("RGB"), dtype=np.uint8)


def to_grayscale(rgb_image: np.ndarray) -> np.ndarray:
    """Convert an RGB image array to grayscale."""
    if rgb_image.ndim != 3 or rgb_image.shape[2] != 3:
        raise ValueError("Expected an RGB image with three color channels.")
    return cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)


def increase_contrast(grayscale: np.ndarray) -> np.ndarray:
    """Increase local contrast with CLAHE while limiting amplification."""
    if grayscale.ndim != 2:
        raise ValueError("Contrast enhancement requires a grayscale image.")
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(grayscale)


def reduce_noise(grayscale: np.ndarray) -> np.ndarray:
    """Reduce small compression artifacts while retaining text edges."""
    if grayscale.ndim != 2:
        raise ValueError("Noise reduction requires a grayscale image.")
    return cv2.fastNlMeansDenoising(grayscale, None, h=7, templateWindowSize=7, searchWindowSize=21)


def apply_threshold(grayscale: np.ndarray) -> np.ndarray:
    """Apply Otsu thresholding to separate likely text from its background."""
    if grayscale.ndim != 2:
        raise ValueError("Thresholding requires a grayscale image.")
    _, thresholded = cv2.threshold(
        grayscale,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    return thresholded


def preprocess_image(
    image: Image.Image,
    use_threshold: bool = True,
) -> np.ndarray:
    """Run the deterministic OCR preprocessing pipeline."""
    grayscale = to_grayscale(pil_to_rgb_array(image))
    contrasted = increase_contrast(grayscale)
    denoised = reduce_noise(contrasted)
    return apply_threshold(denoised) if use_threshold else denoised

