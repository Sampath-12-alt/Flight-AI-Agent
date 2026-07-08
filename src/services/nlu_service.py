"""
Natural Language Understanding (NLU) Service.

Normalizes messy user input before it enters the agent workflow.
Handles spelling mistakes, abbreviations, city aliases, and informal language.

Uses a hybrid approach:
    - Fast local normalizer for common patterns (zero API cost)
    - Gemini LLM fallback for complex/ambiguous cases

Supported normalizations:
    - Spelling corrections: flite → flight, reschdule → reschedule
    - City abbreviations: hyd → Hyderabad, blr → Bangalore
    - Informal language: nxt → next, cheapst → cheapest
    - City aliases: madras → Chennai, calcutta → Kolkata
"""

import re
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import GOOGLE_API_KEY, LLM_MODEL


# ═══════════════════════════════════════════════════════════════
# DICTIONARIES
# ═══════════════════════════════════════════════════════════════

# ── Common Travel Spelling Mistakes ──────────────────────────
# Maps misspelled words to their correct forms.
SPELLING_CORRECTIONS: dict[str, str] = {
    # Flight variations
    "flite": "flight",
    "fligt": "flight",
    "flyt": "flight",
    "fligts": "flights",
    "flites": "flights",
    "fligth": "flight",
    "flght": "flight",
    "flihgt": "flight",
    "filght": "flight",
    "flyght": "flight",
    "flighht": "flight",
    "fliht": "flight",
    # Travel
    "travell": "travel",
    "traval": "travel",
    "travle": "travel",
    "trvl": "travel",
    "trvel": "travel",
    # Reschedule
    "reschdule": "reschedule",
    "reshedule": "reschedule",
    "rescedule": "reschedule",
    "reschudule": "reschedule",
    "reschedul": "reschedule",
    "reshcedule": "reschedule",
    "rechedule": "reschedule",
    "rschedule": "reschedule",
    "reschedle": "reschedule",
    # Booking
    "boooking": "booking",
    "bookin": "booking",
    "bokking": "booking",
    "booknig": "booking",
    "bookng": "booking",
    "bookig": "booking",
    # Search
    "serch": "search",
    "searh": "search",
    "serach": "search",
    "seach": "search",
    # Change/Move
    "chnge": "change",
    "chaneg": "change",
    "chagne": "change",
    "cahnge": "change",
    "mov": "move",
    "moov": "move",
    # Cancel
    "cancell": "cancel",
    "cancle": "cancel",
    "canel": "cancel",
    # Ticket
    "tiket": "ticket",
    "tickt": "ticket",
    "tikket": "ticket",
    "tikt": "ticket",
    # Cheapest / Price
    "cheepest": "cheapest",
    "cheapst": "cheapest",
    "cheepst": "cheapest",
    "chepest": "cheapest",
    "cheapeast": "cheapest",
    "cheep": "cheap",
    # Fastest
    "fastes": "fastest",
    "fastst": "fastest",
    "fastet": "fastest",
    # Direct / Nonstop
    "diret": "direct",
    "dirct": "direct",
    "nonstoop": "nonstop",
    # Show / Find
    "shwo": "show",
    "sohw": "show",
    "fnd": "find",
    "fidn": "find",
    # Want / Need
    "wnt": "want",
    "ned": "need",
    "nedd": "need",
    # Morning / Evening
    "mornig": "morning",
    "morming": "morning",
    "evenig": "evening",
    "evning": "evening",
    # Available
    "availble": "available",
    "avialable": "available",
    "avaliable": "available",
    "avalable": "available",
}

# ── City Name Spelling Corrections ───────────────────────────
# Maps misspelled city names to correct forms.
CITY_SPELLING_CORRECTIONS: dict[str, str] = {
    # Mumbai
    "mumbii": "mumbai",
    "mumabi": "mumbai",
    "mumba": "mumbai",
    "mubai": "mumbai",
    "bombay": "mumbai",
    # Bangalore
    "banglore": "bangalore",
    "bangalor": "bangalore",
    "bangalroe": "bangalore",
    "banglor": "bangalore",
    "bangalure": "bangalore",
    "bengaluru": "bangalore",
    "bengalore": "bangalore",
    # Hyderabad
    "hydrabad": "hyderabad",
    "hyderbad": "hyderabad",
    "hydeabad": "hyderabad",
    "hydrebad": "hyderabad",
    "hyderbad": "hyderabad",
    "hiderabad": "hyderabad",
    "hydarabad": "hyderabad",
    # Delhi
    "dehli": "delhi",
    "dlehi": "delhi",
    "delih": "delhi",
    "dilli": "delhi",
    # Chennai
    "chenai": "chennai",
    "chennei": "chennai",
    "chenni": "chennai",
    "chnnai": "chennai",
    # Kolkata
    "kolkatta": "kolkata",
    "kolkta": "kolkata",
    "kolkatta": "kolkata",
    "colkata": "kolkata",
    # Goa
    "goaa": "goa",
    # Jaipur
    "jaipor": "jaipur",
    "jaipr": "jaipur",
    "japur": "jaipur",
    # Pune
    "pone": "pune",
    "puna": "pune",
    # Ahmedabad
    "ahemdabad": "ahmedabad",
    "ahmdabad": "ahmedabad",
    "amdavad": "ahmedabad",
    # Kochi
    "koci": "kochi",
    "cochin": "kochi",
    # Lucknow
    "luknow": "lucknow",
    "lucnow": "lucknow",
    "luckow": "lucknow",
    # Chandigarh
    "chandigar": "chandigarh",
    "chandigrah": "chandigarh",
    # Visakhapatnam
    "vishakapatnam": "visakhapatnam",
    "vishakhapatnam": "visakhapatnam",
    "vizag": "visakhapatnam",
}

# ── City Abbreviation / Alias Map ────────────────────────────
# Maps short forms and alternative names to canonical city names.
CITY_ALIASES: dict[str, str] = {
    # Common abbreviations
    "hyd": "hyderabad",
    "blr": "bangalore",
    "mum": "mumbai",
    "bom": "mumbai",
    "del": "delhi",
    "ccu": "kolkata",
    "maa": "chennai",
    "goi": "goa",
    "jai": "jaipur",
    "pnq": "pune",
    "amd": "ahmedabad",
    "cok": "kochi",
    "lko": "lucknow",
    "ixc": "chandigarh",
    # Historical / alternate names
    "madras": "chennai",
    "calcutta": "kolkata",
    "bombay": "mumbai",
    "bengaluru": "bangalore",
    "cochin": "kochi",
    "trivandrum": "thiruvananthapuram",
}

# ── Informal Word Normalization ──────────────────────────────
# Maps abbreviations and informal words to standard forms.
INFORMAL_CORRECTIONS: dict[str, str] = {
    "nxt": "next",
    "tmrw": "tomorrow",
    "tmrrow": "tomorrow",
    "tmw": "tomorrow",
    "2morrow": "tomorrow",
    "2mrw": "tomorrow",
    "tomo": "tomorrow",
    "2day": "today",
    "2dy": "today",
    "wknd": "weekend",
    "wkend": "weekend",
    "mnth": "month",
    "wk": "week",
    "yr": "year",
    "frm": "from",
    "frrom": "from",
    "fron": "from",
    "fom": "from",
    "thr": "there",
    "pls": "please",
    "plz": "please",
    "thx": "thanks",
    "thnx": "thanks",
    "abt": "about",
    "btwn": "between",
    "dept": "departure",
    "arr": "arrival",
    "arrvl": "arrival",
    "govt": "government",
    "intl": "international",
    "dom": "domestic",
    "b4": "before",
    "aftr": "after",
    "undr": "under",
    "abv": "above",
}


# ═══════════════════════════════════════════════════════════════
# MAIN NORMALIZATION FUNCTION
# ═══════════════════════════════════════════════════════════════

def normalize_query(raw_query: str) -> dict:
    """
    Normalize a raw user query by correcting spelling, expanding
    abbreviations, and standardizing city names.

    Args:
        raw_query: The original user input.

    Returns:
        dict with:
            "original": str        — The original input
            "normalized": str      — The cleaned/corrected query
            "corrections": list    — List of corrections applied
            "method": str          — "local", "llm", or "none"
            "city_mappings": dict  — Any city aliases resolved
    """
    if not raw_query or not raw_query.strip():
        return {
            "original": raw_query or "",
            "normalized": raw_query or "",
            "corrections": [],
            "method": "none",
            "city_mappings": {},
        }

    original = raw_query.strip()
    corrections = []
    city_mappings = {}

    # Step 1: Local normalization (fast, no API call)
    normalized, local_corrections, local_city_mappings = _normalize_local(original)
    corrections.extend(local_corrections)
    city_mappings.update(local_city_mappings)

    method = "local" if corrections else "none"

    # Step 2: LLM fallback if the query still looks messy
    if GOOGLE_API_KEY and _looks_messy(normalized):
        try:
            llm_result = _normalize_with_llm(normalized, original)
            if llm_result["success"]:
                # Merge LLM corrections with local ones
                normalized = llm_result["normalized"]
                corrections.extend(llm_result["corrections"])
                method = "hybrid" if method == "local" else "llm"
        except Exception as e:
            # LLM failure is non-fatal; use local result
            print(f"⚠️  NLU LLM normalization failed: {e}. Using local result.")

    # If no corrections were made, method stays "none" (passthrough)
    if not corrections:
        method = "none"

    return {
        "original": original,
        "normalized": normalized,
        "corrections": corrections,
        "method": method,
        "city_mappings": city_mappings,
    }


# ═══════════════════════════════════════════════════════════════
# LOCAL NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def _normalize_local(text: str) -> tuple[str, list[str], dict]:
    """
    Perform fast, local text normalization using dictionaries.

    Returns:
        (normalized_text, corrections_list, city_mappings_dict)
    """
    corrections = []
    city_mappings = {}

    # Work with lowercase for matching, but preserve structure
    words = text.split()
    normalized_words = []

    for word in words:
        original_word = word
        # Strip punctuation for matching but preserve it
        clean_word = re.sub(r"[^\w]", "", word.lower())
        punctuation_suffix = word[len(clean_word):] if len(word) > len(clean_word) else ""

        # Reconstruct punctuation handling
        # Extract leading/trailing punctuation
        leading_punct = ""
        trailing_punct = ""
        core = word
        m = re.match(r"^([^\w]*)(.*?)([^\w]*)$", word)
        if m:
            leading_punct, core, trailing_punct = m.groups()
        core_lower = core.lower()

        corrected = core_lower
        was_corrected = False

        # Check informal corrections first (nxt, tmrw, etc.)
        if core_lower in INFORMAL_CORRECTIONS:
            corrected = INFORMAL_CORRECTIONS[core_lower]
            corrections.append(f"'{core}' → '{corrected}' (informal)")
            was_corrected = True

        # Check city aliases (hyd, blr, mum, etc.)
        # Only apply if the word appears in a travel context pattern
        elif core_lower in CITY_ALIASES:
            city_name = CITY_ALIASES[core_lower]
            corrected = city_name
            city_mappings[core_lower] = city_name
            corrections.append(f"'{core}' → '{corrected}' (city alias)")
            was_corrected = True

        # Check city spelling corrections
        elif core_lower in CITY_SPELLING_CORRECTIONS:
            corrected = CITY_SPELLING_CORRECTIONS[core_lower]
            corrections.append(f"'{core}' → '{corrected}' (city spelling)")
            was_corrected = True

        # Check general spelling corrections
        elif core_lower in SPELLING_CORRECTIONS:
            corrected = SPELLING_CORRECTIONS[core_lower]
            corrections.append(f"'{core}' → '{corrected}' (spelling)")
            was_corrected = True

        # Preserve original casing for uncorrected words
        if was_corrected:
            # Title-case city names
            if core_lower in CITY_ALIASES or core_lower in CITY_SPELLING_CORRECTIONS:
                corrected = corrected.title()
            normalized_words.append(f"{leading_punct}{corrected}{trailing_punct}")
        else:
            normalized_words.append(word)

    normalized = " ".join(normalized_words)

    # Additional cleanup: normalize multiple spaces
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized, corrections, city_mappings


def _looks_messy(text: str) -> bool:
    """
    Heuristic to detect if text still looks messy after local normalization.
    Returns True if the text might benefit from LLM cleanup.
    """
    words = text.lower().split()

    # Check for words that don't look like real English
    # (very short words or words with unusual character patterns)
    suspicious_count = 0
    for word in words:
        clean = re.sub(r"[^\w]", "", word)
        if len(clean) <= 1:
            continue  # Skip single chars and punctuation

        # Check for repeated characters (e.g., "boooking")
        if re.search(r"(.)\1{2,}", clean):
            suspicious_count += 1

        # Check for unlikely consonant clusters
        if re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", clean):
            suspicious_count += 1

    # If more than 20% of words look suspicious, try LLM
    return suspicious_count > 0 and (suspicious_count / max(len(words), 1)) > 0.15


# ═══════════════════════════════════════════════════════════════
# LLM NORMALIZATION (FALLBACK)
# ═══════════════════════════════════════════════════════════════

NLU_NORMALIZATION_PROMPT = """You are a text normalization assistant for a travel company's AI agent.

The user has typed a travel-related request with possible spelling mistakes, abbreviations, or informal language.

Your job is to produce a clean, corrected version of the text while preserving the original meaning.

Rules:
- Fix spelling mistakes (e.g., "flite" → "flight", "mumbii" → "Mumbai")
- Expand abbreviations (e.g., "hyd" → "Hyderabad", "nxt" → "next")
- Fix city name spellings (e.g., "banglore" → "Bangalore", "hyderbad" → "Hyderabad")
- Preserve booking IDs exactly as-is (e.g., "BK1024" stays "BK1024")
- Preserve numbers and dates exactly as-is
- Do NOT add information that was not in the original
- Do NOT change the intent or meaning

Original text: "{raw_query}"

Return a JSON object with:
- "normalized": the corrected text
- "corrections": array of strings describing each correction made (e.g., ["'flite' → 'flight'", "'hyd' → 'Hyderabad'"])

Return ONLY the JSON object, no markdown formatting.
"""


def _normalize_with_llm(text: str, original: str) -> dict:
    """
    Use Gemini LLM to normalize text that the local normalizer couldn't
    fully clean.

    Returns:
        dict with "success", "normalized", "corrections"
    """
    import google.generativeai as genai

    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(LLM_MODEL)

    prompt = NLU_NORMALIZATION_PROMPT.format(raw_query=text)
    response = model.generate_content(prompt)
    result_text = response.text.strip()

    # Clean markdown code blocks
    if result_text.startswith("```"):
        result_text = result_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    parsed = json.loads(result_text)
    normalized = parsed.get("normalized", text)
    corrections = parsed.get("corrections", [])

    # Only accept LLM result if it actually changed something
    if normalized.strip().lower() == text.strip().lower():
        return {"success": False, "normalized": text, "corrections": []}

    return {
        "success": True,
        "normalized": normalized,
        "corrections": [f"{c} (llm)" for c in corrections],
    }


# ═══════════════════════════════════════════════════════════════
# STANDALONE TESTING
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n🧠 NLU Service — Normalization Test")
    print("=" * 60)

    test_queries = [
        # Spelling mistakes
        "find fligts hyd to mumbii tommorow",
        "book flyt to delhi",
        "cheepest flight hyd mum",
        "reschdule booking BK1024",
        "flite from hyderbad to mumbai",
        # Abbreviations
        "hyd to banglore nxt week",
        "cheapst flight mum to del",
        "blr to maa tmrw",
        # Informal
        "need flight to mumbai",
        "any direct flights?",
        "show morning flights",
        "need flight under 6000",
        # Mixed
        "cheapest flight from hyd to mum nxt week",
        "chnge my tiket to july 28",
        "mov my flite to friday",
        # City aliases
        "madras to calcutta",
        "bombay to vizag",
        # Clean (should passthrough)
        "Find flights from Delhi to Mumbai next week",
        "My booking ID is BK1024. Change my flight to July 23.",
    ]

    for query in test_queries:
        result = normalize_query(query)
        if result["corrections"]:
            print(f"\n  INPUT:      \"{query}\"")
            print(f"  NORMALIZED: \"{result['normalized']}\"")
            print(f"  METHOD:     {result['method']}")
            print(f"  FIXES:      {', '.join(result['corrections'][:5])}")
        else:
            print(f"\n  INPUT:      \"{query}\"")
            print(f"  RESULT:     ✅ Clean (no changes)")
