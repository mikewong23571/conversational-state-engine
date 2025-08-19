# mypy: ignore-errors

import os

from domains.dialogue.analyzer import LLMAnalyzer, MockAnalyzer
from domains.rendering.incremental import create_renderer
from domains.state.conflicts import ConflictResolver, create_default_detector
from domains.state.context_slicer import ContextSlicer

llm_provider = os.getenv("CSE_LLM_PROVIDER", "mock")
if llm_provider.lower() == "openai" and (
    os.getenv("OPENAI_API_KEY") or os.getenv("CSE_API_KEY")
):
    analyzer_kwargs = {}
    if os.getenv("CSE_MODEL"):
        analyzer_kwargs["model"] = os.getenv("CSE_MODEL")
    if os.getenv("CSE_BASE_URL") or os.getenv("OPENAI_BASE_URL"):
        analyzer_kwargs["base_url"] = os.getenv("CSE_BASE_URL") or os.getenv(
            "OPENAI_BASE_URL"
        )
    if os.getenv("CSE_API_KEY"):
        analyzer_kwargs["api_key"] = os.getenv("CSE_API_KEY")
    analyzer = LLMAnalyzer.create("openai", **analyzer_kwargs)
else:
    analyzer = MockAnalyzer()

markdown_renderer = create_renderer("markdown")
csv_renderer = create_renderer("csv")
context_slicer = ContextSlicer()
conflict_resolver = ConflictResolver()
conflict_detector = create_default_detector()
