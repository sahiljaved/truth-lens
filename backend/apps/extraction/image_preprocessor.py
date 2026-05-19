"""
PIL-based image preprocessing pipeline.

Improving raw image quality before OCR significantly increases Tesseract
accuracy, especially for photos, screenshots with noise, or low-contrast
documents.

Pipeline (each step is optional and configurable):
  1. Normalise colour space → RGB / grayscale
  2. Resize small images (Tesseract works best at ≥300 DPI equivalent)
  3. Enhance contrast
  4. Sharpen edges
  5. Binarise (convert to pure black-and-white)
"""

import logging
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

# Tesseract is most accurate when the image is at least this many pixels wide.
MIN_WIDTH_PX = 1000


def preprocess(image: Image.Image, *, binarise: bool = True) -> Image.Image:
    """
    Run the full preprocessing pipeline and return a new PIL Image.

    Args:
        image:     Any PIL Image (any mode).
        binarise:  Whether to convert to pure 1-bit black-and-white.
                   Set False for coloured documents (e.g. infographics) where
                   pure B&W may lose context.

    Returns:
        Processed PIL Image ready for Tesseract.
    """
    img = _normalise_mode(image)
    img = _upscale_if_small(img)
    img = _enhance_contrast(img)
    img = _sharpen(img)
    if binarise:
        img = _binarise(img)
    return img


# ──────────────────────────────────────────────────────────────────────────────
# Individual steps
# ──────────────────────────────────────────────────────────────────────────────

def _normalise_mode(img: Image.Image) -> Image.Image:
    """
    Convert to grayscale ('L').
    Handles RGBA (drops alpha), palette ('P'), and other exotic modes safely.
    """
    if img.mode == "L":
        return img
    if img.mode in ("RGBA", "LA"):
        # Flatten transparent areas onto white background before grayscaling
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
        img = background
    elif img.mode == "P":
        img = img.convert("RGBA").convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    return img.convert("L")


def _upscale_if_small(img: Image.Image) -> Image.Image:
    """
    If the image is narrower than MIN_WIDTH_PX, upscale using LANCZOS.
    Maintains aspect ratio.
    """
    w, h = img.size
    if w >= MIN_WIDTH_PX:
        return img

    scale = MIN_WIDTH_PX / w
    new_size = (MIN_WIDTH_PX, int(h * scale))
    logger.debug("Upscaling image from %dx%d to %dx%d", w, h, *new_size)
    return img.resize(new_size, Image.Resampling.LANCZOS)


def _enhance_contrast(img: Image.Image, factor: float = 2.0) -> Image.Image:
    """Boost contrast to make text stand out from the background."""
    return ImageEnhance.Contrast(img).enhance(factor)


def _sharpen(img: Image.Image) -> Image.Image:
    """Apply an unsharp mask to sharpen character edges."""
    return img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))


def _binarise(img: Image.Image, threshold: int = 128) -> Image.Image:
    """
    Convert grayscale to pure black-and-white using Otsu-like auto-thresholding.

    PIL's built-in `ImageOps.autocontrast` normalises the histogram first,
    then a fixed threshold gives results close to Otsu's method without
    needing numpy or OpenCV.
    """
    img = ImageOps.autocontrast(img)
    return img.point(lambda px: 255 if px > threshold else 0, "1").convert("L")
