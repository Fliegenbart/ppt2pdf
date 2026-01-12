"""
Image utilities for processing and optimizing images.
"""
import base64
import io
from typing import Optional, Tuple
from PIL import Image


def decode_base64_image(base64_str: str) -> bytes:
    """Decode a base64 string to image bytes."""
    return base64.b64decode(base64_str)


def encode_image_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode('utf-8')


def get_image_dimensions(image_bytes: bytes) -> Tuple[int, int]:
    """Get width and height of an image."""
    img = Image.open(io.BytesIO(image_bytes))
    return img.size


def get_image_format(image_bytes: bytes) -> str:
    """Detect image format from bytes."""
    img = Image.open(io.BytesIO(image_bytes))
    return img.format or "PNG"


def optimize_image(
    image_bytes: bytes,
    max_width: int = 1920,
    max_height: int = 1080,
    quality: int = 85,
) -> bytes:
    """Optimize image for PDF inclusion."""
    img = Image.open(io.BytesIO(image_bytes))

    # Convert RGBA to RGB for JPEG
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background

    # Resize if too large
    if img.width > max_width or img.height > max_height:
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    # Save optimized
    output = io.BytesIO()
    img_format = img.format or "PNG"
    if img_format == "JPEG":
        img.save(output, format="JPEG", quality=quality, optimize=True)
    else:
        img.save(output, format="PNG", optimize=True)

    return output.getvalue()


def convert_to_rgb(image_bytes: bytes) -> bytes:
    """Convert image to RGB mode."""
    img = Image.open(io.BytesIO(image_bytes))

    if img.mode != 'RGB':
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert('RGB')

    output = io.BytesIO()
    img.save(output, format=img.format or "PNG")
    return output.getvalue()


def create_thumbnail(image_bytes: bytes, size: Tuple[int, int] = (200, 200)) -> bytes:
    """Create a thumbnail of an image."""
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail(size, Image.Resampling.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


def get_dominant_color(image_bytes: bytes) -> str:
    """Get the dominant color of an image."""
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert('RGB')
    img = img.resize((50, 50))

    pixels = list(img.getdata())
    r_total = sum(p[0] for p in pixels)
    g_total = sum(p[1] for p in pixels)
    b_total = sum(p[2] for p in pixels)
    count = len(pixels)

    r_avg = r_total // count
    g_avg = g_total // count
    b_avg = b_total // count

    return f"#{r_avg:02x}{g_avg:02x}{b_avg:02x}"


def is_mostly_transparent(image_bytes: bytes, threshold: float = 0.9) -> bool:
    """Check if an image is mostly transparent (likely decorative)."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGBA':
            return False

        alpha = img.split()[3]
        pixels = list(alpha.getdata())
        transparent_count = sum(1 for p in pixels if p < 128)
        return transparent_count / len(pixels) > threshold
    except Exception:
        return False
