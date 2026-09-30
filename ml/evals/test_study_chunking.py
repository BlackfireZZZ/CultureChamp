import json

from study_chunking import block_token_windows, docling_pages, sentence_token_windows


class WordTokenizer:
    def encode(self, text: str):
        return type("Encoding", (), {"ids": list(range(len(text.split())))})()


def test_sentence_token_windows_preserve_text_and_budget() -> None:
    source = "Первое предложение о Бикине. Второе предложение о материале. " * 12
    chunks = sentence_token_windows(source, WordTokenizer(), 16)
    assert len(chunks) > 1
    assert " ".join(chunks) == " ".join(source.split())
    assert all(len(item.split()) <= 16 for item in chunks)


def test_sentence_token_windows_split_oversized_sentence_and_empty_text() -> None:
    tokenizer = WordTokenizer()
    text = " ".join(f"слово{i}" for i in range(35))
    chunks = sentence_token_windows(text, tokenizer, 16)
    assert [len(chunk.split()) for chunk in chunks] == [16, 16, 3]
    assert sentence_token_windows("   ", tokenizer, 16) == ()


def test_block_windows_keep_reading_order_and_skip_empty_layout_blocks() -> None:
    blocks = ["Первый смысловой абзац.", "  ", "Второй абзац. " * 9, "Заголовок."]
    chunks = block_token_windows(blocks, WordTokenizer(), 16)
    assert len(chunks) > 1
    assert " ".join(chunks) == " ".join(" ".join(blocks).split())
    assert all(len(chunk.split()) <= 16 for chunk in chunks)


def test_docling_body_order_excludes_page_furniture(tmp_path) -> None:
    path = tmp_path / "synthetic.json"
    path.write_text(
        json.dumps(
            {
                "pages": {"1": {}},
                "body": {"children": [{"$ref": "#/texts/0"}, {"$ref": "#/groups/0"}]},
                "groups": [{"children": [{"$ref": "#/texts/1"}, {"$ref": "#/texts/2"}]}],
                "texts": [
                    {"label": "text", "text": "Left column", "prov": [{"page_no": 1}]},
                    {"label": "text", "text": "Right column", "prov": [{"page_no": 1}]},
                    {"label": "page_footer", "text": "Page 1", "prov": [{"page_no": 1}]},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert docling_pages(path) == {1: ["Left column", "Right column"]}
