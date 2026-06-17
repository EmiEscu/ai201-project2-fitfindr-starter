"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── query parsing ───────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract a search description, optional size, and optional max_price from a
    natural-language query using lightweight regex rules (no LLM call — keeps
    parsing deterministic, free, and easy to test).

    Returns:
        {"description": str, "size": str | None, "max_price": float | None}
    """
    text = query or ""

    # --- max_price: a number after a price cue (under/below/...), else "$NN" ---
    price_match = re.search(
        r"(?:under|below|less than|max(?:imum)?|up to|<)\s*\$?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    if not price_match:
        price_match = re.search(r"\$\s*(\d+(?:\.\d+)?)", text)
    max_price = float(price_match.group(1)) if price_match else None

    # --- size: prefer explicit "size X"; else a waist token (W27) or a
    # multi-letter size (XXS/XS/XL/XXL). Single letters S/M/L are only honored
    # via the "size X" phrasing to avoid matching them inside ordinary words. ---
    size = None
    size_match = re.search(r"\bsize\s+([A-Za-z0-9/]+)", text, re.IGNORECASE)
    if size_match:
        size = size_match.group(1)
    else:
        token_match = re.search(r"\b(W\d{1,3}|XXS|XS|XXL|XL)\b", text, re.IGNORECASE)
        if token_match:
            size = token_match.group(1)

    # --- description: the query with the matched size/price phrases removed,
    # so they don't pollute the keyword search in search_listings. ---
    description = text
    if price_match:
        description = description.replace(price_match.group(0), " ")
    if size_match:
        description = description.replace(size_match.group(0), " ")
    elif size:
        description = re.sub(
            rf"\b{re.escape(size)}\b", " ", description, flags=re.IGNORECASE
        )
    description = re.sub(r"[,;]+", " ", description)
    description = re.sub(r"\s+", " ", description).strip()

    return {"description": description, "size": size, "max_price": max_price}


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1: fresh session — the single source of truth for this interaction.
    session = _new_session(query, wardrobe)

    # Step 2: parse the query into description / size / max_price (regex-based).
    session["parsed"] = _parse_query(query)
    parsed = session["parsed"]

    # Step 3: search listings with the parsed parameters.
    session["search_results"] = search_listings(
        parsed["description"], parsed["size"], parsed["max_price"]
    )

    # Branch: no matches → set a fatal error and return early. We do NOT call
    # suggest_outfit / create_fit_card when there's nothing to style.
    if not session["search_results"]:
        desc = parsed["description"] or query
        session["error"] = (
            f"No listings matched '{desc}'. "
            "Try a different description or raising your budget."
        )
        return session

    # Step 4: select the top (most relevant) result.
    session["selected_item"] = session["search_results"][0]

    # Step 5: suggest an outfit. Returns a real wardrobe-based outfit, general
    # styling advice (empty wardrobe), or None (LLM call failed).
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], wardrobe
    )

    # Step 6: build the fit card. Only weave a REAL wardrobe-based outfit into
    # the caption — i.e. the wardrobe had items AND suggest_outfit succeeded.
    # For an empty wardrobe (general advice) or a failed suggest_outfit (None),
    # pass outfit=None so create_fit_card writes an item-only caption.
    wardrobe_has_items = bool(wardrobe and wardrobe.get("items"))
    fit_outfit = (
        session["outfit_suggestion"]
        if wardrobe_has_items and session["outfit_suggestion"]
        else None
    )
    session["fit_card"] = create_fit_card(fit_outfit, session["selected_item"])

    # Step 7: return the completed session.
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
