from io import BytesIO

from PIL import Image


MAX_FILE_SIZE = 200 * 1024

ARTWORK_RULES = {
    "poster": {
        "width": 600,
        "height": 900,
        "ratio": 2 / 3,
    },
    "banner": {
        "width": 1280,
        "height": 720,
        "ratio": 16 / 9,
    },
    "thumbnail": {
        "width": 640,
        "height": 360,
        "ratio": 16 / 9,
    },
}


ALLOWED_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}


def validate_artwork(
    file_bytes: bytes,
    artwork_type: str,
):
    """
    Validate an artwork file before it is stored.

    Returns:
        (True, None) when valid
        (False, error_message) when invalid
    """

    if artwork_type not in ARTWORK_RULES:
        return (
            False,
            f"Unsupported artwork type: {artwork_type}",
        )

    # Check file size
    if len(file_bytes) > MAX_FILE_SIZE:
        size_kb = len(file_bytes) / 1024

        return (
            False,
            (
                f"File is too large ({size_kb:.1f} KB). "
                "Maximum allowed size is 200 KB."
            ),
        )

    if len(file_bytes) == 0:
        return False, "The uploaded file is empty."

    # Try opening the image
    try:
        image = Image.open(BytesIO(file_bytes))
        image.verify()

    except Exception:
        return (
            False,
            "The uploaded file is not a valid image.",
        )

    # Re-open after verify()
    try:
        image = Image.open(BytesIO(file_bytes))

    except Exception:
        return (
            False,
            "The uploaded image could not be read.",
        )

    # Check image format
    if image.format not in ALLOWED_FORMATS:
        return (
            False,
            (
                f"Unsupported image format: {image.format}. "
                "Use JPEG, PNG, or WEBP."
            ),
        )

    width, height = image.size

    rules = ARTWORK_RULES[artwork_type]

    expected_width = rules["width"]
    expected_height = rules["height"]
    expected_ratio = rules["ratio"]

    # Check dimensions
    if width != expected_width or height != expected_height:
        return (
            False,
            (
                f"{artwork_type.title()} must be "
                f"{expected_width}x{expected_height}px. "
                f"Received {width}x{height}px."
            ),
        )

    # Check aspect ratio
    actual_ratio = width / height

    if abs(actual_ratio - expected_ratio) > 0.01:
        return (
            False,
            (
                f"{artwork_type.title()} has an invalid "
                f"aspect ratio. Expected "
                f"{expected_ratio:.2f}."
            ),
        )

    return True, None