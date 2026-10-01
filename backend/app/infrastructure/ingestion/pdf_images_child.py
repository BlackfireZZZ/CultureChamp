"""Resource-limited extraction of embedded PDF raster images."""

import base64
import io
import json
import resource
import sys

from PIL import Image
from pypdf import PdfReader

MAX_IMAGES = 32
MAX_PAGES = 200
MAX_PIXELS = 4_000_000
MAX_IMAGE_BYTES = 1_000_000


def main() -> int:
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        data = sys.stdin.buffer.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            return 2
        reader = PdfReader(io.BytesIO(data), strict=True)
        if not 1 <= len(reader.pages) <= MAX_PAGES:
            return 2
        found: list[list[int | str]] = []
        for page_number, page in enumerate(reader.pages, 1):
            for ordinal, item in enumerate(page.images):
                image = item.image
                if image is None or image.width * image.height > MAX_PIXELS:
                    return 2
                output = io.BytesIO()
                image.convert("RGB").save(output, format="PNG", optimize=True)
                content = output.getvalue()
                if len(content) > MAX_IMAGE_BYTES:
                    return 2
                found.append([page_number, ordinal, base64.b64encode(content).decode("ascii")])
                if len(found) > MAX_IMAGES:
                    return 2
        json.dump(found, sys.stdout)
        return 0
    except (Exception, MemoryError):
        return 2


if __name__ == "__main__":
    sys.exit(main())
