"""Compare located PDF text layers without exporting held source passages."""

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from app.infrastructure.ingestion.pdf_text import extract_pdf_pages

ROOT = Path(__file__).resolve().parents[2]
TOKEN = re.compile(r"\w+", re.UNICODE)
LINE_HYPHEN = re.compile(r"(?<=\w)[\u002d\u2010\u2011]\s*\n\s*(?=\w)")


def normalized_tokens(text: str) -> list[str]:
    dehyphenated = LINE_HYPHEN.sub("", text)
    return TOKEN.findall(unicodedata.normalize("NFKC", dehyphenated).casefold())


def compare_texts(first: str, second: str) -> dict[str, float | int]:
    a, b = normalized_tokens(first), normalized_tokens(second)
    if not a or not b:
        raise ValueError("both text layers must contain words")
    shared_unordered = sum((Counter(a) & Counter(b)).values())
    ordered = sum(block.size for block in SequenceMatcher(
        None, a, b, autojunk=False
    ).get_matching_blocks())
    return {
        "first_tokens": len(a),
        "second_tokens": len(b),
        "unordered_first_coverage": round(shared_unordered / len(a), 4),
        "unordered_second_coverage": round(shared_unordered / len(b), 4),
        "ordered_first_coverage": round(ordered / len(a), 4),
        "ordered_second_coverage": round(ordered / len(b), 4),
    }


def poppler_pages(path: Path) -> list[str]:
    result = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(path), "-"],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Poppler extraction failed")
    pages = result.stdout.decode("utf-8").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def audit(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = []
    for source_id, relative_path in manifest["source_files"].items():
        path = ROOT / relative_path
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != manifest["source_hashes"][source_id]:
            raise ValueError(f"fixture hash changed: {source_id}")
        pypdf = extract_pdf_pages(content)
        poppler = poppler_pages(path)
        if len(pypdf) != len(poppler):
            raise ValueError(f"page count differs: {source_id}")
        pages = []
        for extracted, text in zip(pypdf, poppler, strict=True):
            if extracted.locator.page != len(pages) + 1:
                raise ValueError("pypdf physical page numbering changed")
            pages.append({"page": extracted.locator.page, **compare_texts(extracted.text, text)})
        sources.append({"source_id": source_id, "sha256": manifest["source_hashes"][source_id],
                        "pages": pages})
    return {
        "comparison": "pypdf-content-order_vs_poppler-default-order",
        "normalization": "NFKC casefold words; join line-end hyphenation",
        "interpretation": "Parser agreement only; neither text layer is ground truth",
        "sources": sources,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "ml/evals/manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"sources": len(report["sources"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
