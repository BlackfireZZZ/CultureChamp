"""Counterexamples for local extraction, span preservation and original hashing."""

import hashlib
import json
import zipfile

import pytest
from corpus import build, chunks, extract, normalize


def test_normalization_repairs_line_hyphens_only():
    assert normalize("Культу-\nра\t наро-\nдов и тёмно-синий") == (
        "Культура народов и тёмно-синий"
    )


def test_chunks_retain_exact_offsets_and_do_not_join_pages():
    units = [{"source_id": "s", "source_hash": "h", "locator": str(i),
              "text": "один два три четыре пять"} for i in (1, 2)]
    result = chunks(units, words=3, overlap=1)
    assert len(result) == 4
    assert [r["text"] for r in result] == ["один два три", "три четыре пять"] * 2
    assert len({r["key"] for r in result}) == 4
    for row in result:
        assert units[0]["text"][row["start"]:row["end"]] == row["text"]
    with pytest.raises(ValueError):
        chunks(units, words=3, overlap=3)


def test_epub_uses_spine_order_and_excludes_script(tmp_path):
    path = tmp_path / "example.epub"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("META-INF/container.xml", '<container><rootfile full-path="OPS/book.opf"/>'
                   '</container>')
        z.writestr("OPS/book.opf", '<package xmlns="urn:opf"><manifest>'
                   '<item id="a" href="a.xhtml"/><item id="b" href="b.xhtml"/>'
                   '</manifest><spine><itemref idref="b"/><itemref idref="a"/>'
                   '</spine></package>')
        z.writestr("OPS/a.xhtml", '<p>Первый &amp; второй</p><script>hidden</script>')
        z.writestr("OPS/b.xhtml", '<h1>Заголовок</h1><p>Текст</p>')
    assert extract(path) == [("epub:spine:1:OPS/b.xhtml", "Заголовок Текст"),
                             ("epub:spine:2:OPS/a.xhtml", "Первый & второй")]


def test_hash_mismatch_fails_before_extraction(tmp_path):
    source = tmp_path / "file.pdf"
    source.write_bytes(b"changed")
    (tmp_path / "inventory.json").write_text(json.dumps([
        {"path": str(source), "sha256": hashlib.sha256(b"original").hexdigest()}
    ]))
    with pytest.raises(ValueError, match="Source hash changed"):
        build(tmp_path)
