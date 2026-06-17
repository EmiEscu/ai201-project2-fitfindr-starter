"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import logging
import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

logger = logging.getLogger(__name__)

# Groq model used by the LLM-backed tools (suggest_outfit, create_fit_card).
_MODEL = "llama-3.3-70b-versatile"


# Common words that carry no search signal — dropped before scoring so they
# don't inflate a listing's relevance score.
_STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "of", "in", "on", "to", "i",
    "im", "looking", "want", "need", "some", "any", "my", "me", "is", "are",
    "that", "this", "under", "over", "size", "please", "find", "show",
}


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # 1. Extract meaningful keywords from the user's description.
    keywords = {
        word
        for word in re.findall(r"[a-z0-9]+", (description or "").lower())
        if word not in _STOPWORDS
    }

    scored = []
    for listing in listings:
        # 2a. Price filter — skip anything above the ceiling (inclusive).
        if max_price is not None and listing.get("price", 0) > max_price:
            continue

        # 2b. Size filter — case-insensitive substring match so "M" hits "S/M".
        if size is not None:
            listing_size = (listing.get("size") or "").lower()
            if size.strip().lower() not in listing_size:
                continue

        # 3. Score by keyword overlap with title, description, and style_tags.
        haystack = " ".join(
            [
                listing.get("title", ""),
                listing.get("description", ""),
                " ".join(listing.get("style_tags", [])),
            ]
        ).lower()
        haystack_words = set(re.findall(r"[a-z0-9]+", haystack))
        score = len(keywords & haystack_words)

        # 4. Drop listings with no relevant matches.
        if score > 0:
            scored.append((score, listing))

    # 5. Sort by score, highest first, and return just the listing dicts.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    item_summary = (
        f"- Title: {new_item.get('title', 'unknown item')}\n"
        f"- Category: {new_item.get('category', 'unknown')}\n"
        f"- Colors: {', '.join(new_item.get('colors', [])) or 'unspecified'}\n"
        f"- Style tags: {', '.join(new_item.get('style_tags', [])) or 'none'}\n"
        f"- Description: {new_item.get('description', '')}"
    )

    items = wardrobe.get("items", []) if wardrobe else []

    # 1. Empty wardrobe → general styling advice (no specific pieces to reference).
    if not items:
        logger.warning("suggest_outfit called with an empty wardrobe; "
                       "giving general styling advice.")
        prompt = (
            "You are a thoughtful personal stylist. A shopper is considering "
            "this secondhand item:\n\n"
            f"{item_summary}\n\n"
            "They have not added any wardrobe pieces yet. In 1-2 sentences, give "
            "general styling advice: what kinds of pieces pair well with it and "
            "what vibe or occasion it suits. Be specific and encouraging. Do not "
            "invent specific items they own."
        )
    else:
        # 3. Non-empty wardrobe → reference specific pieces by name.
        wardrobe_lines = []
        for w in items:
            colors = ", ".join(w.get("colors", []))
            tags = ", ".join(w.get("style_tags", []))
            wardrobe_lines.append(
                f"- {w.get('name', 'item')} ({w.get('category', '?')}; "
                f"colors: {colors or 'n/a'}; style: {tags or 'n/a'})"
            )
        wardrobe_text = "\n".join(wardrobe_lines)
        prompt = (
            "You are a thoughtful personal stylist. A shopper is considering "
            "this secondhand item:\n\n"
            f"{item_summary}\n\n"
            "Here is their current wardrobe:\n"
            f"{wardrobe_text}\n\n"
            "In 1-2 sentences, suggest one complete outfit that pairs this new "
            "item with specific pieces from their wardrobe (refer to the pieces "
            "by name) and explain how the combination works. Be specific and "
            "natural — no bullet lists."
        )

    # 2 & 4. Call the LLM; on any failure return None so the fit card can still run.
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        advice = response.choices[0].message.content.strip()
        # For the empty-wardrobe case, nudge the user toward richer results.
        if not items:
            advice += (
                "\n\nFor more personalized suggestions, "
                "try filling up your wardrobe file."
            )
        return advice
    except Exception as exc:
        logger.warning("suggest_outfit LLM call failed: %s", exc)
        return None


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 1–3 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, do NOT raise an exception — instead
        generate a creative caption focused entirely on the new_item.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Detect an empty or whitespace-only outfit string and, if so, build a
           fallback prompt focused only on the new_item (no wardrobe pairing).
        2. Otherwise build a prompt that gives the LLM the item details and the
           outfit, and asks for a caption matching the style guidelines above.
        3. Call the LLM (higher temperature for variety) and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Item details every caption needs (name, price, platform) plus vibe cues.
    title = new_item.get("title", "this find")
    price = new_item.get("price")
    price_str = f"${price:.0f}" if isinstance(price, (int, float)) else "a steal"
    platform = new_item.get("platform", "online")
    style_tags = ", ".join(new_item.get("style_tags", [])) or "one-of-a-kind"
    colors = ", ".join(new_item.get("colors", [])) or "great"
    description = new_item.get("description", "")

    item_details = (
        f"- Name: {title}\n"
        f"- Price: {price_str}\n"
        f"- Platform: {platform}\n"
        f"- Colors: {colors}\n"
        f"- Style: {style_tags}\n"
        f"- Description: {description}"
    )

    # 1. Empty/whitespace-only outfit → caption focused only on the new item.
    if not outfit or not outfit.strip():
        logger.warning("create_fit_card called without an outfit suggestion; "
                       "writing a caption for the item alone.")
        prompt = (
            "Write a casual, authentic 1-3 sentence social media caption (think "
            "Instagram/TikTok OOTD post) for this secondhand fashion find:\n\n"
            f"{item_details}\n\n"
            "Capture the vibe of the piece and naturally mention its name, price, "
            "and the platform it's from (each once). Sound like a real person "
            "hyping a great thrift score — not a product listing. Be creative and "
            "fresh. Return only the caption text."
        )
    else:
        # 2. Outfit available → caption that ties the item to the styling idea.
        prompt = (
            "Write a casual, authentic 1-3 sentence social media caption (think "
            "Instagram/TikTok OOTD post) for this secondhand fashion find:\n\n"
            f"{item_details}\n\n"
            f"Styling idea to weave in: {outfit.strip()}\n\n"
            "Capture the vibe, naturally mention the item's name, price, and the "
            "platform it's from (each once), and hint at how it pairs with the "
            "styling idea above. Sound like a real person hyping a great thrift "
            "score — not a product listing. Be creative and fresh. Return only "
            "the caption text."
        )

    # 3. Call the LLM with a higher temperature so captions vary each run.
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=160,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("create_fit_card LLM call failed: %s", exc)
        # Last-resort caption so the UI always has something shareable.
        return (
            f"Just scored this {title} for {price_str} on {platform} — "
            "obsessed already."
        )
