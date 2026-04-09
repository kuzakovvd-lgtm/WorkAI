from __future__ import annotations

from pathlib import Path

from WorkAI.knowledge_base.indexer import parse_markdown_article


def test_parse_title_from_markdown_heading(tmp_path: Path) -> None:
    path = tmp_path / "ghost_time.md"
    path.write_text("# Ghost Time\n\nHow to detect ghost time.", encoding="utf-8")

    article = parse_markdown_article(path)

    assert article.title == "Ghost Time"
    assert "How to detect ghost time." in article.body
    assert article.tags == []


def test_fallback_title_from_filename(tmp_path: Path) -> None:
    path = tmp_path / "methodology_note.md"
    path.write_text("No top heading here.", encoding="utf-8")

    article = parse_markdown_article(path)

    assert article.title == "methodology_note"


def test_extract_tags_from_frontmatter_csv(tmp_path: Path) -> None:
    path = tmp_path / "with_tags.md"
    path.write_text(
        "---\n"
        "tags: ghost, assess, quality\n"
        "---\n"
        "# Trust\n"
        "Body text\n",
        encoding="utf-8",
    )

    article = parse_markdown_article(path)

    assert article.title == "Trust"
    assert article.tags == ["ghost", "assess", "quality"]


def test_extract_tags_empty_when_missing(tmp_path: Path) -> None:
    path = tmp_path / "empty_tags.md"
    path.write_text("# Doc\n\nBody", encoding="utf-8")

    article = parse_markdown_article(path)

    assert article.tags == []
