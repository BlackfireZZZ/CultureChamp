"""Bounded parent interface to the isolated PDF image extractor."""

import base64
import binascii
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.infrastructure.ingestion.pdf_text import ExtractionError

PARSER_PATH = Path(__file__).with_name("pdf_images_child.py")
MAX_RESULT_BYTES = 45 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ExtractedVisual:
    page: int
    ordinal: int
    png: bytes


def extract_pdf_images(data: bytes) -> tuple[ExtractedVisual, ...]:
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(PARSER_PATH)],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=25,
            cwd="/",
            env={"PYTHONIOENCODING": "utf-8"},
            check=False,
        )
        if result.returncode != 0 or len(result.stdout) > MAX_RESULT_BYTES:
            raise ExtractionError("PDF image extraction failed")
        raw = json.loads(result.stdout)
        if not isinstance(raw, list) or len(raw) > 32:
            raise ValueError("invalid image count")
        images = []
        for item in raw:
            page, ordinal, encoded = item
            if (
                type(page) is not int or not 1 <= page <= 200
                or type(ordinal) is not int or not 0 <= ordinal < 32
                or not isinstance(encoded, str)
            ):
                raise ValueError("invalid image locator")
            content = base64.b64decode(encoded, validate=True)
            if not content.startswith(b"\x89PNG\r\n\x1a\n") or len(content) > 1_000_000:
                raise ValueError("invalid image content")
            images.append(ExtractedVisual(page, ordinal, content))
        return tuple(images)
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, binascii.Error) as exc:
        raise ExtractionError("PDF image extraction failed") from exc
