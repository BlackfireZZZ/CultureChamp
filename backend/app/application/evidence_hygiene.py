"""Conservative screening for explicit role and instruction overrides in evidence."""

import re
import unicodedata

_CONTROL_PATTERNS = (
    re.compile(r"\b(?:ignore|disregard)\s+(?:all\s+)?(?:previous\s+)?"
               r"(?:rules|instructions)\b"),
    re.compile(r"\b(?:reveal|print|show)\s+(?:the\s+)?(?:system|developer)\s+"
               r"(?:prompt|message|instructions)\b"),
    re.compile(r"\bигнорируй(?:те)?\s+(?:(?:все|всё)\s+)?"
               r"(?:(?:предыдущие|системные)\s+)?(?:инструкции|правила)\b"),
    re.compile(r"\b(?:покажи|раскрой)(?:те)?\s+(?:системный|скрытый)\s+"
               r"(?:промпт|запрос|инструкции)\b"),
    re.compile(r"<\|im_start\|>|<\|im_end\|>|\[\s*system\s*\]|"
               r"(?m:^\s*(?:system|developer)\s*:)"),
)


def has_explicit_prompt_control(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return any(pattern.search(normalized) is not None for pattern in _CONTROL_PATTERNS)
