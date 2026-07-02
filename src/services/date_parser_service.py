"""
Date Parser Service.

Interprets natural language date expressions into concrete YYYY-MM-DD dates.
Uses LLM for complex phrases, with deterministic fallback for common patterns.

Supported patterns:
    - "tomorrow"
    - "next week" / "this week"
    - "weekend" / "this weekend" / "next weekend"
    - "next month"
    - "any day in August"
    - "July 15" / "15 July" / "2026-07-15"
    - Date ranges: "July 10 to July 15"
"""

import re
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import GOOGLE_API_KEY, LLM_MODEL


# ── Main Interface ────────────────────────────────────────────

def parse_flexible_dates(date_phrase: str, reference_date: datetime | None = None) -> dict:
    """
    Convert a flexible date phrase into a list of concrete dates.

    Args:
        date_phrase: Natural language date (e.g., "next week", "tomorrow")
        reference_date: Reference date for relative calculations (defaults to today)

    Returns:
        dict with:
            "success": bool,
            "dates": list[str],          # YYYY-MM-DD dates
            "interpretation": str,       # Human-readable description
            "method": str,               # "keyword" or "llm"
            "error": str | None
    """
    if not date_phrase or not date_phrase.strip():
        return {
            "success": False,
            "dates": [],
            "interpretation": "",
            "method": "none",
            "error": "No date phrase provided.",
        }

    ref = reference_date or datetime.now()
    phrase = date_phrase.strip().lower()

    # Try keyword-based parsing first (fast, no API call)
    result = _parse_keyword(phrase, ref)
    if result["success"]:
        return result

    # Try LLM-based parsing for complex phrases
    if GOOGLE_API_KEY:
        try:
            return _parse_with_llm(date_phrase, ref)
        except Exception as e:
            print(f"⚠️  LLM date parsing failed: {e}. Using fallback.")

    # Final fallback: try to extract any date-like pattern
    return _parse_fallback(date_phrase, ref)


# ── Keyword-Based Parser ─────────────────────────────────────

def _parse_keyword(phrase: str, ref: datetime) -> dict:
    """Parse common date phrases using keyword matching."""

    # ── Exact date: YYYY-MM-DD ────────────────────────────────
    iso_match = re.search(r"\d{4}-\d{2}-\d{2}", phrase)
    if iso_match:
        date_str = iso_match.group(0)
        return _success([date_str], f"Specific date: {date_str}", "keyword")

    # ── "today" ───────────────────────────────────────────────
    if phrase in ["today", "today's flights", "flights today"]:
        d = ref.strftime("%Y-%m-%d")
        return _success([d], f"Today ({d})", "keyword")

    # ── "tomorrow" ────────────────────────────────────────────
    if phrase in ["tomorrow", "tmrw", "tomorrow's flights"]:
        d = (ref + timedelta(days=1)).strftime("%Y-%m-%d")
        return _success([d], f"Tomorrow ({d})", "keyword")

    # ── "day after tomorrow" ──────────────────────────────────
    if "day after tomorrow" in phrase:
        d = (ref + timedelta(days=2)).strftime("%Y-%m-%d")
        return _success([d], f"Day after tomorrow ({d})", "keyword")

    # ── "this week" ───────────────────────────────────────────
    if phrase in ["this week", "this week's flights"]:
        dates = _get_remaining_week_dates(ref)
        return _success(dates, f"This week ({len(dates)} days)", "keyword")

    # ── "next weekend" (MUST check before "next week") ────────
    if "next weekend" in phrase:
        dates = _get_next_weekend(ref)
        return _success(dates, f"Next weekend ({len(dates)} days)", "keyword")

    # ── "next week" ───────────────────────────────────────────
    if "next week" in phrase:
        dates = _get_next_week_dates(ref)
        return _success(dates, f"Next week (Mon-Sun, {len(dates)} days)", "keyword")

    # ── "this weekend" ────────────────────────────────────────
    if phrase in ["this weekend", "weekend", "the weekend"]:
        dates = _get_this_weekend(ref)
        return _success(dates, f"This weekend ({len(dates)} days)", "keyword")

    # ── "next month" ──────────────────────────────────────────
    if "next month" in phrase:
        dates = _get_next_month_dates(ref)
        return _success(dates, f"Next month ({len(dates)} days)", "keyword")

    # ── "any day in <month>" ──────────────────────────────────
    month_match = re.search(
        r"(?:any\s+day\s+in|anytime\s+in|in)\s+(january|february|march|april|may|june|"
        r"july|august|september|october|november|december)",
        phrase,
    )
    if month_match:
        month_name = month_match.group(1)
        dates = _get_month_dates(month_name, ref)
        return _success(dates, f"All days in {month_name.title()} ({len(dates)} days)", "keyword")

    # ── "Month Day" or "Day Month" (specific date) ───────────
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    for mname, mnum in months_map.items():
        # "July 15" or "july 15th"
        m = re.search(rf"{mname}\s+(\d{{1,2}})(?:st|nd|rd|th)?", phrase)
        if m:
            day = int(m.group(1))
            year = ref.year if mnum >= ref.month else ref.year + 1
            d = f"{year}-{mnum:02d}-{day:02d}"
            return _success([d], f"{mname.title()} {day} ({d})", "keyword")
        # "15 July" or "15th July"
        m = re.search(rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+{mname}", phrase)
        if m:
            day = int(m.group(1))
            year = ref.year if mnum >= ref.month else ref.year + 1
            d = f"{year}-{mnum:02d}-{day:02d}"
            return _success([d], f"{mname.title()} {day} ({d})", "keyword")

    # No keyword match
    return {"success": False, "dates": [], "interpretation": "", "method": "none", "error": ""}


# ── LLM-Based Parser ─────────────────────────────────────────

def _parse_with_llm(date_phrase: str, ref: datetime) -> dict:
    """Use Gemini LLM to interpret complex date phrases."""
    import google.generativeai as genai

    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(LLM_MODEL)

    prompt = f"""You are a date interpretation assistant. Convert the following date phrase into a list of specific dates.

Today's date is: {ref.strftime("%Y-%m-%d")} ({ref.strftime("%A")})

Date phrase: "{date_phrase}"

Return a JSON object with:
- "dates": array of date strings in YYYY-MM-DD format
- "interpretation": a brief human-readable description of what dates you selected

Rules:
- If the phrase refers to a range (e.g., "next week"), list ALL dates in that range.
- If the phrase is a single date, return an array with one element.
- Maximum 31 dates (one month).
- Only return future dates (today or later).
- Return ONLY the JSON object, no markdown formatting.
"""

    response = model.generate_content(prompt)
    result_text = response.text.strip()

    # Clean markdown code blocks
    if result_text.startswith("```"):
        result_text = result_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    parsed = json.loads(result_text)
    dates = parsed.get("dates", [])
    interpretation = parsed.get("interpretation", date_phrase)

    if not dates:
        return {
            "success": False, "dates": [], "interpretation": interpretation,
            "method": "llm", "error": "LLM could not determine dates.",
        }

    return _success(dates, interpretation, "llm")


# ── Fallback Parser ──────────────────────────────────────────

def _parse_fallback(date_phrase: str, ref: datetime) -> dict:
    """Last resort: try to extract any date-like pattern."""
    # Try DD/MM/YYYY or MM/DD/YYYY
    slash_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_phrase)
    if slash_match:
        d, m, y = slash_match.groups()
        date_str = f"{y}-{int(m):02d}-{int(d):02d}"
        return _success([date_str], f"Parsed date: {date_str}", "fallback")

    # Default to tomorrow if nothing works
    d = (ref + timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "success": True,
        "dates": [d],
        "interpretation": f"Could not interpret '{date_phrase}'. Defaulting to tomorrow ({d}).",
        "method": "fallback",
        "error": None,
    }


# ── Date Generation Helpers ──────────────────────────────────

def _get_remaining_week_dates(ref: datetime) -> list[str]:
    """Get remaining days of the current week (today through Sunday)."""
    weekday = ref.weekday()  # Monday=0, Sunday=6
    days_left = 6 - weekday
    dates = []
    for i in range(days_left + 1):
        d = ref + timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates


def _get_next_week_dates(ref: datetime) -> list[str]:
    """Get all 7 days of next week (Monday to Sunday)."""
    # Find next Monday
    days_until_monday = (7 - ref.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = ref + timedelta(days=days_until_monday)

    dates = []
    for i in range(7):
        d = next_monday + timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates


def _get_this_weekend(ref: datetime) -> list[str]:
    """Get Saturday and Sunday of the current week."""
    weekday = ref.weekday()
    days_to_saturday = (5 - weekday) % 7
    if days_to_saturday == 0 and weekday > 5:
        days_to_saturday = 7
    saturday = ref + timedelta(days=days_to_saturday)
    sunday = saturday + timedelta(days=1)
    return [saturday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")]


def _get_next_weekend(ref: datetime) -> list[str]:
    """Get Saturday and Sunday of next week."""
    this_weekend = _get_this_weekend(ref)
    # Add 7 days
    from datetime import datetime as dt
    dates = []
    for d_str in this_weekend:
        d = dt.strptime(d_str, "%Y-%m-%d")
        next_d = d + timedelta(days=7)
        dates.append(next_d.strftime("%Y-%m-%d"))
    return dates


def _get_next_month_dates(ref: datetime) -> list[str]:
    """Get all dates in the next calendar month."""
    if ref.month == 12:
        next_month = 1
        next_year = ref.year + 1
    else:
        next_month = ref.month + 1
        next_year = ref.year

    dates = []
    day = 1
    while True:
        try:
            d = datetime(next_year, next_month, day)
            dates.append(d.strftime("%Y-%m-%d"))
            day += 1
        except ValueError:
            break
    return dates


def _get_month_dates(month_name: str, ref: datetime) -> list[str]:
    """Get all dates in a specified month."""
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    month_num = months_map.get(month_name.lower(), 0)
    if month_num == 0:
        return []

    year = ref.year if month_num >= ref.month else ref.year + 1

    dates = []
    day = 1
    while True:
        try:
            d = datetime(year, month_num, day)
            # Only include today or future dates
            if d.date() >= ref.date():
                dates.append(d.strftime("%Y-%m-%d"))
            day += 1
        except ValueError:
            break
    return dates


def _success(dates: list[str], interpretation: str, method: str) -> dict:
    """Build a successful result."""
    return {
        "success": True,
        "dates": dates,
        "interpretation": interpretation,
        "method": method,
        "error": None,
    }


# ── Standalone Testing ────────────────────────────────────────
if __name__ == "__main__":
    from datetime import datetime

    print("\n📅 Date Parser Service — Test")
    print("=" * 60)

    test_phrases = [
        "tomorrow",
        "next week",
        "this weekend",
        "next weekend",
        "next month",
        "any day in August",
        "July 15",
        "2026-08-10",
        "day after tomorrow",
    ]

    for phrase in test_phrases:
        result = parse_flexible_dates(phrase)
        dates_str = ", ".join(result["dates"][:5])
        if len(result["dates"]) > 5:
            dates_str += f" ... (+{len(result['dates'])-5} more)"
        print(f"\n  \"{phrase}\"")
        print(f"    → {result['interpretation']}")
        print(f"    → [{dates_str}]")
        print(f"    → Method: {result['method']}")
