import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

THEMES_CACHE = "cache/themes_cache.json"

TAXONOMY_TEXT = """
Level 1 → Level 2 sub-themes:

Quality of Service → Attention to Detail, Speed and Efficiency, Tire Installation, Alignment, Tire Pressure, Wheel, Valve Stem Caps, Incorrect Service, Hubcaps, Spare Tire, TPMS Sensors
Customer Service → Professionalism (ONLY explicit employee behavior/attitude), Knowledge, Loyalty (ONLY explicit returning/not returning mentions), Recognition (ONLY when employee name is mentioned)
Customer Concerns / Feedback → Issue Resolution, Improvement Suggestions, Perceived Upselling
Store Environment → Cleanliness, Organization, Atmosphere, Amenities
Time → Wait Times, Quoted Inaccurate Wait Time, Appointment Not Honored
"""

SYSTEM_PROMPT = f"""You are a brand analytics classifier for Discount Tire customer reviews.
Classify each comment into ONE Level 1 category and ONE Level 2 sub-theme.

Taxonomy:
{TAXONOMY_TEXT}

Classification rules:
- Professionalism: ONLY for explicit employee behavior or attitude mentions
- Recognition: ONLY when a specific employee name is given
- Loyalty: ONLY for explicit statements about returning or not returning
- If ambiguous, default to: Quality of Service → Attention to Detail
- Sentiment: positive, neutral, or negative

Return ONLY a valid JSON array. No markdown, no explanation, no extra text."""


def _load_cache() -> dict:
    if os.path.exists(THEMES_CACHE):
        try:
            with open(THEMES_CACHE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    os.makedirs("cache", exist_ok=True)
    with open(THEMES_CACHE, "w") as f:
        json.dump(cache, f, indent=2)


def _default_result(comment_id: str, rating=None) -> dict:
    return {
        "comment_id": comment_id,
        "level1": "Quality of Service",
        "level2": "Attention to Detail",
        "sentiment": "neutral",
        "rating": rating,
    }


def analyze_themes_batch(
    comments: list[dict],
    batch_size: int = 20,
    force_refresh: bool = False,
) -> dict:
    """Classify comments with Claude.  Returns {id: {level1, level2, sentiment, rating}}."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set; skipping theme analysis")
        return {c.get("id", ""): _default_result(c.get("id", ""), c.get("rating")) for c in comments}

    client = anthropic.Anthropic(api_key=api_key)
    cache = {} if force_refresh else _load_cache()
    results: dict = {}

    to_process: list[dict] = []
    for c in comments:
        cid = c.get("id", "")
        if cid in cache and not force_refresh:
            results[cid] = cache[cid]
        else:
            to_process.append(c)

    for i in range(0, len(to_process), batch_size):
        batch = to_process[i : i + batch_size]
        payload = [
            {"id": c["id"], "text": str(c.get("comment_text", ""))[:500]}
            for c in batch
        ]

        prompt = (
            f"Classify each of the {len(batch)} comments below.\n"
            f"Return a JSON array with exactly {len(batch)} objects, each with keys: "
            f"comment_id, level1, level2, sentiment.\n\n"
            f"Comments:\n{json.dumps(payload, ensure_ascii=False)}"
        )

        try:
            # Use prompt caching on the stable system prompt
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": prompt}],
            )

            raw = message.content[0].text.strip()
            # Strip markdown fences if present
            if "```" in raw:
                raw = raw.split("```")[1].lstrip("json").strip()
                raw = raw.split("```")[0].strip()

            batch_results: list[dict] = json.loads(raw)

            for result in batch_results:
                cid = result.get("comment_id", "")
                original = next((c for c in batch if c["id"] == cid), None)
                if original:
                    result["rating"] = original.get("rating")
                results[cid] = result
                cache[cid] = result

        except Exception as e:
            logger.error(f"Theme batch error (batch {i//batch_size + 1}): {e}")
            for c in batch:
                cid = c["id"]
                results[cid] = _default_result(cid, c.get("rating"))

    _save_cache(cache)
    return results
