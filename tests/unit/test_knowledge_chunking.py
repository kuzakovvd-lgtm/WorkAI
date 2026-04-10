from __future__ import annotations

import pytest
from WorkAI.knowledge_base.chunking import chunk_text


def test_chunk_text_empty() -> None:
    assert chunk_text("   \n\t  ") == []


def test_chunk_text_splits_large_text() -> None:
    source = ("word " * 1500).strip()
    chunks = chunk_text(source, max_chars=300, overlap=50)

    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)


def test_chunk_text_validates_params() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", max_chars=0)
    with pytest.raises(ValueError):
        chunk_text("abc", max_chars=100, overlap=100)

