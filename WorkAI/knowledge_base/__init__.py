"""Knowledge base public API for indexing and FTS lookup."""

from WorkAI.knowledge_base.indexer import index_knowledge_sources
from WorkAI.knowledge_base.lookup import clear_lookup_cache, lookup_methodology

__all__ = ["clear_lookup_cache", "index_knowledge_sources", "lookup_methodology"]
