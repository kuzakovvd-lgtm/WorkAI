from __future__ import annotations

from pathlib import Path

import pytest
from WorkAI.knowledge_base import extractors
from WorkAI.knowledge_base.models import KnowledgeArticleDocument


def test_parse_article_document_dispatch_md(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    path.write_text("# Title\n\nBody", encoding="utf-8")

    article = extractors.parse_article_document(path)

    assert article.title == "Title"
    assert article.body == "Body"


def test_parse_article_document_dispatch_docx(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "a.docx"
    path.write_bytes(b"stub")

    expected = KnowledgeArticleDocument(
        source_path=str(path),
        title="Docx",
        body="Body",
        tags=[],
    )

    monkeypatch.setattr(extractors, "parse_docx_article", lambda p: expected)

    article = extractors.parse_article_document(path)

    assert article == expected


def test_parse_article_document_dispatch_pdf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "a.pdf"
    path.write_bytes(b"stub")

    expected = KnowledgeArticleDocument(
        source_path=str(path),
        title="Pdf",
        body="Body",
        tags=[],
    )

    monkeypatch.setattr(extractors, "parse_pdf_article", lambda p: expected)

    article = extractors.parse_article_document(path)

    assert article == expected


def test_parse_article_document_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported knowledge source extension"):
        extractors.parse_article_document(path)


def test_supported_extensions_contains_md_docx_pdf() -> None:
    assert extractors.SUPPORTED_KNOWLEDGE_EXTENSIONS == (".md", ".docx", ".pdf")
