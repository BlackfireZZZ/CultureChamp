"""Derive a concise first-turn title from the user's subject, not template boilerplate."""

import re

IMAGE_SUBJECT = re.compile(
    r"изображени[еяй]\s+(.+?)(?=\s+(?:по теме|по материалам|на основе|с опорой)|[.!?\n]|$)",
    re.IGNORECASE,
)
IMAGE_TOPIC = re.compile(r"(?:по теме|по материалам о)\s+(.+?)(?=[.!?\n]|$)", re.IGNORECASE)


def _filled_value(match: re.Match[str] | None) -> str:
    if match is None:
        return ""
    raw = match.group(1)
    if "[" in raw or "]" in raw:
        return ""
    return raw.strip().strip("\"'«»").rstrip(" ,.;:")


def first_turn_title(text: str, starter_id: str | None) -> str:
    if starter_id == "UC-03" or re.search(r"(?:промпт|изображени)", text, re.IGNORECASE):
        subject = _filled_value(IMAGE_SUBJECT.search(text))
        topic = _filled_value(IMAGE_TOPIC.search(text))
        if subject or topic:
            suffix = " · ".join(part for part in (subject, topic) if part)
            return _shorten(f"Изображение: {suffix}")
        if starter_id == "UC-03":
            return "Промпт для изображения"
    return _shorten(text.splitlines()[0].strip())


def _shorten(value: str) -> str:
    if len(value) <= 60:
        return value
    return value[:57].rsplit(" ", 1)[0].rstrip(" ,.;:") or value[:60]
