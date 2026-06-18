"""
Pytest tests for the three FitFindr tools.

The LLM-backed tools (suggest_outfit, create_fit_card) are tested with a FAKE
Groq client so the suite runs offline and deterministically — no GROQ_API_KEY
and no network required. There is at least one test per failure mode:

    search_listings  → no matches returns []  (+ price/size filter checks)
    suggest_outfit   → empty wardrobe returns advice string; LLM error returns None
    create_fit_card  → empty/None outfit doesn't crash; LLM error returns fallback

Run from the project root with:  pytest tests/
"""

import pytest

import tools
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── Shared test data ────────────────────────────────────────────────────────

SAMPLE_ITEM = {
    "id": "lst_test",
    "title": "Y2K Baby Tee — Butterfly Print",
    "description": "Cute early-2000s baby tee with a butterfly graphic.",
    "category": "tops",
    "style_tags": ["y2k", "vintage", "graphic tee"],
    "size": "S/M",
    "condition": "excellent",
    "price": 18.0,
    "colors": ["white", "pink"],
    "brand": None,
    "platform": "depop",
}


# ── Fake Groq client so LLM tools run offline ────────────────────────────────

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self._content = content

    def create(self, **kwargs):  # mirrors client.chat.completions.create(...)
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class _FakeGroqClient:
    """Minimal stand-in for the Groq client that returns canned text."""

    def __init__(self, content):
        self.chat = _FakeChat(content)


@pytest.fixture
def fake_llm(monkeypatch):
    """Patch _get_groq_client so the LLM returns a fixed string."""

    def _install(content="Pair it with high-waisted jeans for a cute look."):
        monkeypatch.setattr(
            tools, "_get_groq_client", lambda: _FakeGroqClient(content)
        )

    return _install


@pytest.fixture
def failing_llm(monkeypatch):
    """Patch _get_groq_client so any LLM call raises an exception."""

    def boom():
        raise RuntimeError("simulated Groq API failure")

    monkeypatch.setattr(tools, "_get_groq_client", boom)


# ── Tool 1: search_listings (pure, no LLM) ───────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    # FAILURE MODE: nothing matches → empty list, no exception raised.
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    # max_price is enforced strictly (inclusive).
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter_case_insensitive():
    # "m" should match a listing sized "S/M" (case-insensitive substring).
    results = search_listings("y2k baby tee", size="m", max_price=None)
    assert len(results) > 0
    assert all("m" in (item["size"] or "").lower() for item in results)


# ── Tool 2: suggest_outfit ───────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe_returns_string(fake_llm):
    fake_llm("Style it with the baggy jeans and chunky white sneakers.")
    result = suggest_outfit(SAMPLE_ITEM, get_example_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


def test_suggest_outfit_empty_wardrobe_returns_advice_with_nudge(fake_llm):
    # FAILURE MODE: empty wardrobe → general advice STRING (not None),
    # ending with the "fill up your wardrobe file" nudge line.
    fake_llm("This tee pairs well with high-waisted denim.")
    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""
    assert result.strip().endswith("try filling up your wardrobe file.")


def test_suggest_outfit_llm_failure_returns_none(failing_llm):
    # FAILURE MODE: LLM call raises → tool returns None (does not crash).
    result = suggest_outfit(SAMPLE_ITEM, get_example_wardrobe())
    assert result is None


# ── Tool 3: create_fit_card ──────────────────────────────────────────────────

def test_create_fit_card_with_outfit_returns_string(fake_llm):
    fake_llm("Obsessed with this thrifted tee — total Y2K energy!")
    result = create_fit_card("Pair with baggy jeans and chunky sneakers.", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""


def test_create_fit_card_empty_outfit_does_not_crash(fake_llm):
    # FAILURE MODE: empty/whitespace/None outfit → item-only caption, no crash.
    fake_llm("Just scored this cute tee!")
    for empty_outfit in ("", "   ", None):
        result = create_fit_card(empty_outfit, SAMPLE_ITEM)
        assert isinstance(result, str)
        assert result.strip() != ""


def test_create_fit_card_llm_failure_returns_fallback(failing_llm):
    # FAILURE MODE: LLM call raises → templated fallback caption, no crash.
    result = create_fit_card("Pair with jeans.", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert SAMPLE_ITEM["title"] in result
    assert SAMPLE_ITEM["platform"] in result
