# FitFindr — Starter Kit

## DEMO VIDEO: https://www.youtube.com/watch?v=09mIfbBeNuE
## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
|── .gitignore                 # Git ignore file
|── agent.py                   # Connect tools through a planning loop.
|── app.py                     # Interface Using gradio  
|── README.md                  # Instructions and informatio of the project 
|── tools.py                   # Location of the 3 tools the agent uses
├── planning.md                # Planning file
└── requirements.txt           # Python dependencies
```

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# or: .venv\Scripts\activate    # Windows CMD
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## Where to Start

1. **Read `planning.md` to undestand the logic**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Run `python app.py`.

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```
## Tools

---

**1. `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`**

**Purpose**: Search the mock listings dataset for items matching the description, optional size, and optional price ceiling.

**Input parameters:**
- `description` (str): Natural Language Model matches the description the user types in "vintage graphic tee". This will then be matched to the title, description, and style_tags.
- `size` (str): Size string to filter by (e.g., "M", "W30", "8"). Case-insensitive. Pass None to skip size filtering.
- `max_price` (float): Max price in dollars. Pass None to skip filter.

**Returns**: `list[dict]` -- List is form of `dict` that represent different listings. Each dict contains `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns [] on no match; never raises.

**Example Query**

This is an example for a query such as "I'm looking for high-waisted vintage denim shorts size W27 under $30" 

**Output example**

```python
"id": "lst_016",
"title": "High-Waisted Denim Shorts — Cutoff",
"description": "DIY cutoff denim shorts from Levi's 501s. Raw hem, slightly frayed. High-waisted. Perfect summer length.",
"category": "bottoms",
"style_tags": ["vintage", "denim", "summer", "classic"],
"size": "W27",
"condition": "good",
"price": 24.00,
"colors": ["light blue", "blue"],
"brand": "Levi's",
"platform": "poshmark"
```
**2. `suggest_outfit(new_item: dict, wardrobe: dict) -> str`**

**Purpose**: Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits for them to use with their selected item.

**Input parameters:**
- `new_item` (dict): this represents the results from tool one. All the attributes of the listing we pulled from the users query.
- `wardrobe` (dict): A list of dicts with 'items' as the key. There are two dicts an example_wardrobe that has a complete list of dicts with different items. 

**Returns**: Non empty suggestion `str` with outfit suggestions. On empty wardrobes it returns general styling advice rather than failing.

**Example (With Wardrobe)**
```python
item = search_listings("high-waisted vintage denim shorts", size="W27", max_price=30)[0]
print(suggest_outfit(item, get_example_wardrobe()))
```

**Example Output**
```bash
Pairing the High-Waisted Denim Shorts with the White Ribbed Tank Top 
and Chunky White Sneakers creates a classic summer outfit that 
balances casual comfort with a touch of vintage charm, as the raw 
hem of the shorts adds a laid-back vibe to the crisp, fitted tank 
top and clean sneakers. The overall look is completed by adding the 
Brown Leather Belt, which adds a warm, earthy tone to the outfit and 
defines the waist, creating a cohesive and effortless summer 
ensemble.
```

**Example (Without Wardrobe)**
```python
item = search_listings("high-waisted vintage denim shorts", size="W27", max_price=30)[0] 
print(suggest_outfit(item, get_empty_wardrobe()))
```

**Example Output**
```bash
suggest_outfit called with an empty wardrobe; giving general styling
advice.

These high-waisted denim shorts are perfect for creating a
laid-back, summery look, and they'll pair beautifully with a variety
of tops, such as graphic tees, breezy blouses, or cropped sweaters
for a casual, effortless vibe. They're ideal for warm-weather
outings, like picnics, beach trips, or outdoor concerts, and can
easily be dressed up or down to suit your personal style and the
occasion.

For more personalized suggestions, try filling up your wardrobe file.
```

**3. `create_fit_card(outfit: str, new_item: dict) -> str`**

**Purpose**: Generate a short, shareable outfit caption for the thrifted find.

**Input parameters:**
- `outfit` (str): A short paragraph generated by the previous tool. 
- `new_item` (dict): This will be the dict containing the new item that they got. This will have 'title', 'price' and 'platform' of the piece.

**Returns**: A 1-3 sentence `str` caption for any social media. The caption includes the item name, price, and platform. The fit card only weaves in a real wardrobe-based outfit. If the wardrobe was empty (so `suggest_outfit` only produced general styling advice) or `suggest_outfit` returned `None`, the agent calls `create_fit_card` with `outfit=None`, and the tool produces an item-only caption focused entirely on the `new_item`.

**Example Ouput: 90s track jacket in size M (with wardrobe)**
```
Just scored the cutest 90s Track Jacket for $45 on Poshmark and I'm
obsessing over how it levels up my fave baggy jeans and chunky
whites - the navy and white stripes are literally the perfect add-on
for a comfy, nostalgic vibe that's so on point.
```

**Example Output: 90s track jacket in size M (without wardrobe)**
```
Just scored the cutest 90s Track Jacket — Navy/White Stripe on
Poshmark for $45 and I'm obsessed with the vintage vibes, perfect
for layering on a chill day. The stripe detail down the sleeves is
everything. Authentic 90s style doesn't get much better than this
```
## Planning Loop

The agent runs one linear pass per query and **branches on what `search_listings` returns** — it never fires all three tools blindly. Each step reads from and writes to the shared session dict (see [State Management](#state-management)).

1. **Start a session.** `_new_session()` creates a fresh session dict to hold everything this query produces.
2. **Parse the query.** `_parse_query()` uses lightweight regex (no LLM) to pull out `description`, `size`, and `max_price` — price from cues like "under $30"/"$30", size from "size M" or tokens like `W27`/`XXS`/`XL`.
3. **Clean the description.** The matched size and price phrases are stripped out of the description so they don't skew the keyword search.
4. **Search the listings.** `search_listings()` runs with the three parsed parameters and stores the relevance-ranked matches.
5. **Branch on the results.** If nothing matched, the agent records a friendly error, **stops early, and never calls the LLM tools.** Otherwise it continues.
6. **Pick the top match.** The highest-ranked listing becomes the `selected_item` that the next two tools build on.
7. **Suggest an outfit.** `suggest_outfit()` pairs the item with the user's wardrobe; an empty wardrobe still returns useful general styling advice instead of failing.
8. **Create the fit card.** `create_fit_card()` writes the shareable caption — weaving in a real wardrobe outfit when there is one, or falling back to an item-only caption otherwise.
9. **Finish.** The completed session is returned, and its results fill the three UI panels.

## State Management

Everything a query produces lives in one **session dictionary** that the loop hands from step to step — the single source of truth for the run. Each tool reads what it needs from the session and writes its result back, so the user never re-enters anything and nothing gets recomputed downstream. The keys fill up in roughly this order:

| Key | Written by | Holds |
|-----|-----------|-------|
| `query` | session init | the raw user text |
| `parsed` | `_parse_query()` | the extracted `description`, `size`, `max_price` |
| `search_results` | `search_listings()` | the relevance-ranked list of matches |
| `selected_item` | the loop | the top match — what the rest of the run is about |
| `wardrobe` | session init | the wardrobe chosen for this run |
| `outfit_suggestion` | `suggest_outfit()` | styling text (or `None` if its LLM call failed) |
| `fit_card` | `create_fit_card()` | the final shareable caption |
| `error` | the loop | set only on a fatal stop (no listings found) |

**How it flows:** the *same* `selected_item` object is handed to `suggest_outfit` and then to `create_fit_card` — the exact dict, not a copy or a re-fetch, which is how you can prove state is passing rather than being rebuilt. `outfit_suggestion` carries the styling text between those two steps, and only a genuine wardrobe-based outfit is fed into the caption (general advice or a `None` result yields an item-only fit card). The moment `error` is set, the loop returns immediately and the UI shows just that message.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query returns `[]` | Session error will rise and return early so no other tools are called. We will prompt the user with: "No listings matched '<description>'. Try a different description or raising your budget." |
| suggest_outfit | Wardrobe is empty, or LLM call raises an exception| If the wardrobe is empty, `suggest_outfit` offers general styling advice for the item rather than returning an empty string, and we prompt the user to "Try adding more items into wardrobe file for more tailored suggestions" then move on to `create_fit_card`. If an LLM call exception is raised, `suggest_outfit` returns `None` and the agent CONTINUES (this is not a fatal `session["error"]`, which is reserved for the no-results case that ends the loop early). `session["outfit_suggestion"]` stays `None`, and `handle_query` surfaces a friendly note in the Outfit panel: "Couldn't generate an outfit suggestion right now — please try again in a moment." The fit card is still produced (item-only, since `outfit=None` is passed). |
| create_fit_card | Outfit input is missing or incomplete | since `suggest_outfit` is returns `None` we will default and simply create a short caption for the `new_item` using the `description`, `style_tags`, `price`, and `platform` to create a caption that captures the 'vibe' of the item |

### Concrete examples (from the tests)

Each failure mode below is covered by a test in `tests/test_tools.py` and was confirmed by hand.

**`search_listings` — no results:**
```python
search_listings("designer ballgown", size="XXS", max_price=5)   # → []
```
`run_agent` then sets `session["error"]` and stops early (no LLM tools called):
```
No listings matched 'designer ballgown'. Try a different description or raising your budget.
```

**`suggest_outfit` — empty wardrobe:** returns general advice (not `None`), ending with the nudge line:
```python
suggest_outfit(item, get_empty_wardrobe())
# → "...pair beautifully with graphic tees, breezy blouses... For more
#    personalized suggestions, try filling up your wardrobe file."
```

**`suggest_outfit` — LLM call raises:** the tool swallows the error and returns `None`, so the run continues:
```python
suggest_outfit(item, get_example_wardrobe())   # LLM unreachable → None
```

**`create_fit_card` — empty/missing outfit:** no crash; it writes an item-only caption instead:
```python
create_fit_card("", item)
# → "Just scored this Y2K Baby Tee — Butterfly Print for $18 on depop..."
```

---

## Spec Reflection

**One way the spec helped:** The specs made it so much easier to understand what I was building. Working on the `planning.md` file didn't just make it easier to work with Claude, but it also helped me understand how the agent would work with each tool and what the role of each tool would be. The thing that helped me the most was the `planning.md` architecture because I was able to use it as a little roadmap when I would get stuck.

**One divergence and why:** The initial `create_fit_card` docstring said it should return an error message when `suggest_outfit` gave it nothing. I diverged: I had it generate an item-only fallback caption instead. My reasoning was that we'd already added a graceful fallback to `suggest_outfit` (general styling advice instead of an error), so `create_fit_card` should stay consistent and still produce something usable rather than an error.

---

## AI Usage

**Instance 1 — `suggest_outfit` change in architecture**

I gave Claude the Tool 2 spec block from `planning.md`, the docstring from `tools.py`, the loaders from  `utils/data_loader.py` and I asked it to implement `suggest_outfit` in `tools.py`.

Once it had returned code, I reviewed and noticed Claude caught a major logic conflict between my `planning.md` file and the docstring from `tools.py`. Initially my `planning.md` said `suggest_outfit` should return `None` if the wardrobe was empty, while the `tools.py` docstring said it should give general styling advice. Claude caught that conflict; I chose the general-advice behavior and updated `planning.md`.

What I changed: I took Claudes advice and made the changes to the `suggest_outfit` architecture and corrected my whole `planning.md` file to properly reflect those new changes. 

**Instance 2 — Planning loop and `session["error"]` handling in `agent.py`**

For Milestone 4 I gave Claude the `agent.py` stub with its TODO steps, the Planning Loop, State Management, and Architecture (decision tree) sections of my `planning.md`, and the finished `tools.py` for context, and asked it to implement `run_agent()` and `handle_query()`.

Before writing the loop, Claude flagged a logic conflict in my error handling. My `planning.md` said that if `suggest_outfit`'s LLM call failed, the agent should record the error in `session["error"]`. But `handle_query` treats `session["error"]` as a fatal stop — it shows only that message and blanks the other two panels — so that rule would have hidden the fit card whenever the outfit step had a recoverable hiccup.

What I changed: I kept `session["error"]` reserved for the fatal no-results case that ends the loop early, and let a failed `suggest_outfit` simply leave `outfit_suggestion` as `None` so the run continues, with `handle_query` showing a friendly note in the Outfit panel instead. I then updated my `planning.md` (Error Handling, State Management, and the diagram) so the spec matched this behavior, and reviewed the generated loop to confirm it branches on `search_listings` and does not call the other tools when there are no matches.
