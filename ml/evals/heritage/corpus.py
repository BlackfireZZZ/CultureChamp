"""Local-only source extraction and immutable character-span passage locators."""

import hashlib
import json
import re
import subprocess
import unicodedata
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    text = re.sub(r"(?<=[а-яА-ЯёЁ])-\s*\n\s*(?=[а-яА-ЯёЁ])", "", text)
    return re.sub(r"\s+", " ", text).strip()


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.skip += 1
        if tag in {"p", "br", "div", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
        if tag in {"p", "div", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def extract(path: Path) -> list[tuple[str, str]]:
    if path.suffix.lower() == ".pdf":
        result = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", str(path), "-"],
            check=True, capture_output=True, text=True, timeout=120,
        )
        pages = result.stdout.split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        return [(f"pdf:page:{i}", normalize(t)) for i, t in enumerate(pages, 1)]
    with zipfile.ZipFile(path) as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next(x for x in container.iter() if x.tag.endswith("rootfile"))
        package_path = rootfile.attrib["full-path"]
        package = ET.fromstring(archive.read(package_path))
        items = {x.attrib["id"]: x.attrib["href"] for x in package.iter()
                 if x.tag.endswith("}item")}
        rows = []
        for i, item in enumerate((x for x in package.iter()
                                  if x.tag.endswith("}itemref")), 1):
            member = str(Path(package_path).parent / items[item.attrib["idref"]])
            parser = TextParser()
            parser.feed(archive.read(member).decode("utf-8-sig"))
            rows.append((f"epub:spine:{i}:{member}", normalize("".join(parser.parts))))
        return rows


def build(store: Path) -> list[dict]:
    inventory = json.loads((store / "inventory.json").read_text())
    units = []
    for source in inventory:
        path = Path(source["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Source hash changed")
        for locator, text in extract(path):
            units.append({"source_id": source["source_id"], "source_hash": source["sha256"],
                          "format": source["format"], "locator": locator, "text": text})
    (store / "units.json").write_text(json.dumps(units, ensure_ascii=False))
    return units


def chunks(units: list[dict], words: int = 120, overlap: int = 30) -> list[dict]:
    if words <= 0 or not 0 <= overlap < words:
        raise ValueError("Invalid window")
    rows = []
    for unit in units:
        tokens = list(re.finditer(r"\S+", unit["text"]))
        for start in range(0, len(tokens), words - overlap):
            if start and start + overlap >= len(tokens):
                break
            end = min(start + words, len(tokens))
            a, b = tokens[start].start(), tokens[end - 1].end()
            rows.append({**unit, "start": a, "end": b,
                         "key": f"{unit['source_id']}:{unit['locator']}:{a}-{b}",
                         "text": unit["text"][a:b]})
    return rows


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("store", type=Path)
    parser.add_argument("--manifest", type=Path, help="Initialize inventory from public hashes")
    parser.add_argument("--sample", action="store_true", help="Print bounded private excerpts")
    args = parser.parse_args()
    if args.manifest and not (args.store / "inventory.json").exists():
        metadata = json.loads(args.manifest.read_text())
        inventory = [{**source, "path": str((args.store / "raw" / source["filename"]).resolve())}
                     for source in metadata["sources"]]
        for source in inventory:
            if hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError("Source hash differs from the public manifest")
        (args.store / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False))
    units = build(args.store)
    print(json.dumps({"units": len(units), "characters": sum(len(u["text"]) for u in units),
                      "chunks120": len(chunks(units))}))
    if args.sample:
        inventory = json.loads((args.store / "inventory.json").read_text())
        for source in inventory:
            selected = [u for u in units if u["source_id"] == source["source_id"]
                        and len(u["text"]) > 1600]
            print(source["source_id"], source["filename"])
            for fraction in (0.30, 0.65):
                unit = selected[min(len(selected)-1, int(len(selected)*fraction))]
                offset = int(len(unit["text"]) * (0.30 if fraction == 0.30 else 0.55))
                print(unit["locator"], offset, unit["text"][offset:offset+400])
