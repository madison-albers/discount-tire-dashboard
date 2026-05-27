import json
import logging
import os
from datetime import datetime

import anthropic
import pandas as pd

logger = logging.getLogger(__name__)

HEADLINE_CACHE        = "cache/headline_cache.json"
THEME_SUMMARIES_CACHE = "cache/theme_summaries.json"
AI_PERCEPTION_CACHE   = "cache/ai_perception_cache.json"

# Five platform-insight cards for the AI Perception Monitor
# Structure: q_id → (display_title, badge_css_class, question_text)
PERCEPTION_QUESTIONS: dict[str, tuple[str, str, str]] = {
    "trustpilot": (
        "Trustpilot",
        "perc-badge-tp",
        "Based on your training data, what are the most common themes in Discount Tire's "
        "Trustpilot reviews? What do reviewers praise and complain about most? "
        "Give specific examples of the types of comments left.",
    ),
    "consumeraffairs": (
        "ConsumerAffairs",
        "perc-badge-ca",
        "Based on your training data, what patterns do you see in Discount Tire's "
        "ConsumerAffairs reviews? What are the most frequent complaints and how are "
        "they typically resolved?",
    ),
    "competitive": (
        "Competitive Landscape",
        "perc-badge-comp",
        "Based on Trustpilot and ConsumerAffairs reviews in your training data, how does "
        "Discount Tire's customer service reputation compare to competitors like Firestone "
        "and Goodyear?",
    ),
    "ratings": (
        "Rating Patterns",
        "perc-badge-ratings",
        "What star rating patterns do you see for Discount Tire on Trustpilot and "
        "ConsumerAffairs — are reviews mostly 1-star and 5-star with little in between? "
        "What drives each extreme?",
    ),
    "bbb": (
        "BBB Complaints",
        "perc-badge-bbb",
        "Based on your training data, what types of complaints are most commonly filed "
        "against Discount Tire on the Better Business Bureau? How are they typically resolved?",
    ),
}

SYSTEM_BRAND = """You are a senior brand analytics strategist for Discount Tire.
Deliver concise, executive-level insights. Be specific. Use numbers when available.
Avoid generic platitudes — every sentence should be actionable or revealing."""

SYSTEM_PERCEPTION = (
    "You are a brand research analyst with deep knowledge of consumer review platforms. "
    "Answer questions about Discount Tire's online reputation based solely on your training data. "
    "Be specific, balanced, and cite concrete examples where possible. "
    "Keep each answer to 3-5 concise sentences."
)


def _get_client() -> anthropic.Anthropic | None:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)


def _load_json_cache(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_json_cache(path: str, data: dict) -> None:
    os.makedirs("cache", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Headline insight ──────────────────────────────────────────────────────────

def generate_headline_insight(df: pd.DataFrame, force_refresh: bool = False) -> str:
    if df.empty:
        return "Sync Reddit data to generate executive insights."

    cache_key = f"headline_{datetime.now().strftime('%Y-%m-%d')}"
    if not force_refresh:
        cache = _load_json_cache(HEADLINE_CACHE)
        if cache_key in cache:
            return cache[cache_key]

    client = _get_client()
    if not client:
        return "Add ANTHROPIC_API_KEY to .env to enable AI-generated insights."

    total    = len(df)
    sources  = df["source"].value_counts().to_dict() if "source" in df.columns else {}
    sentiments = (
        df["sentiment"].value_counts().to_dict()
        if "sentiment" in df.columns and df["sentiment"].notna().any()
        else {}
    )

    pos_themes = neg_themes = "N/A"
    if "sentiment" in df.columns and "level2" in df.columns:
        pos_df = df[df["sentiment"] == "positive"]
        neg_df = df[df["sentiment"] == "negative"]
        if not pos_df.empty:
            pos_themes = str(pos_df["level2"].value_counts().head(5).to_dict())
        if not neg_df.empty:
            neg_themes = str(neg_df["level2"].value_counts().head(5).to_dict())

    prompt = f"""Write a 4-5 sentence executive summary of Discount Tire's Reddit brand voice.

Data (Reddit only):
- Total posts/comments: {total}
- Subreddits: {sources}
- Sentiment breakdown: {sentiments}
- Top positive themes: {pos_themes}
- Top negative themes: {neg_themes}

Be direct, specific, and executive-ready. No bullet points — flowing prose."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=[{"type": "text", "text": SYSTEM_BRAND, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        insight = message.content[0].text.strip()
        cache   = _load_json_cache(HEADLINE_CACHE)
        cache[cache_key] = insight
        _save_json_cache(HEADLINE_CACHE, cache)
        return insight
    except Exception as e:
        logger.error(f"Headline generation failed: {e}")
        return f"Insight generation failed: {e}"


# ── Per-theme summary ─────────────────────────────────────────────────────────

def generate_theme_summary(theme_name: str, comments: list[str], force_refresh: bool = False) -> str:
    if not comments:
        return f"No comments available for '{theme_name}'."

    cache_key = f"{theme_name}_{datetime.now().strftime('%Y-%m-%d')}"
    if not force_refresh:
        cache = _load_json_cache(THEME_SUMMARIES_CACHE)
        if cache_key in cache:
            return cache[cache_key]

    client = _get_client()
    if not client:
        return f"Add ANTHROPIC_API_KEY to enable AI summaries for '{theme_name}'."

    sample = "\n".join([f"- {c[:300]}" for c in comments[:15]])
    prompt = f"""Summarize in 2-3 sentences what Reddit users say about '{theme_name}' for Discount Tire.
Be specific about recurring patterns, pain points, or praise.

Comments:
{sample}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=[{"type": "text", "text": SYSTEM_BRAND, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        summary = message.content[0].text.strip()
        cache   = _load_json_cache(THEME_SUMMARIES_CACHE)
        cache[cache_key] = summary
        _save_json_cache(THEME_SUMMARIES_CACHE, cache)
        return summary
    except Exception as e:
        logger.error(f"Theme summary failed: {e}")
        return f"Summary unavailable for '{theme_name}'."


# ── Chat assistant ────────────────────────────────────────────────────────────

def chat_with_reviews(messages: list[dict], df: pd.DataFrame) -> str:
    print(f"[Chat] called — {len(messages)} messages, df rows: {len(df)}")

    client = _get_client()
    if not client:
        msg = "ANTHROPIC_API_KEY not set — add it to .env to enable the AI assistant."
        print(f"[Chat] {msg}")
        return msg

    try:
        # Build data context — all inside try so any error is caught cleanly
        ctx_parts: list[str] = []
        if not df.empty:
            ctx_parts.append(f"Total Reddit posts/comments in view: {len(df)}")

            if "subreddit" in df.columns and df["subreddit"].notna().any():
                ctx_parts.append(
                    f"Subreddits: {df['subreddit'].value_counts().head(5).to_dict()}"
                )
            elif "source" in df.columns:
                ctx_parts.append(f"Source: {df['source'].value_counts().to_dict()}")

            if "sentiment" in df.columns and df["sentiment"].notna().any():
                ctx_parts.append(f"Sentiment: {df['sentiment'].value_counts().to_dict()}")

            if "level1" in df.columns and df["level1"].notna().any():
                ctx_parts.append(
                    f"Top themes: {df['level1'].value_counts().head(5).to_dict()}"
                )

            if "date" in df.columns:
                dates = pd.to_datetime(df["date"], errors="coerce").dropna()
                if not dates.empty:
                    ctx_parts.append(
                        f"Date range: {dates.min().strftime('%b %Y')} – "
                        f"{dates.max().strftime('%b %Y')}"
                    )

        context = "\n".join(ctx_parts) if ctx_parts else "No Reddit data loaded yet."
        system = (
            "You are a customer intelligence analyst for Discount Tire. "
            "You have access to live Reddit data provided below. "
            "You also have knowledge from your training data about what customers say about "
            "Discount Tire on Trustpilot, ConsumerAffairs, and the Better Business Bureau.\n\n"
            "When answering:\n"
            "- For Reddit questions: reference the actual live data provided below\n"
            "- For Trustpilot / ConsumerAffairs / BBB questions: draw on your training data "
            "knowledge and be specific about themes and examples you have seen\n"
            "- Always be specific — cite themes, quote real examples, and give counts where available\n"
            "- Give actionable business insights, not just descriptions\n"
            "- Clearly label whether your answer is based on LIVE REDDIT DATA or "
            "AI TRAINING DATA KNOWLEDGE\n\n"
            f"LIVE REDDIT DATA CONTEXT:\n{context}"
        )

        print(f"[Chat] calling claude-sonnet-4-6 …")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
        reply = response.content[0].text.strip()
        print(f"[Chat] response received ({len(reply)} chars): {reply[:120]}…")
        return reply

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        print(f"[Chat] ERROR: {e}")
        return f"⚠️ Claude API error: {e}"


# ── AI Perception Monitor ─────────────────────────────────────────────────────

def fetch_ai_perception(force_refresh: bool = False) -> dict[str, str]:
    """
    Query Claude for each PERCEPTION_QUESTIONS entry once per day.
    Returns {q_id: answer_text}.
    force_refresh=True deletes the cache file and re-queries all questions.
    """
    cache_key = datetime.now().strftime("%Y-%m-%d")

    if not force_refresh:
        cache = _load_json_cache(AI_PERCEPTION_CACHE)
        if cache_key in cache:
            return cache[cache_key]

    client = _get_client()
    if not client:
        return {
            q_id: "Add ANTHROPIC_API_KEY to .env to enable AI Platform Insights."
            for q_id in PERCEPTION_QUESTIONS
        }

    answers: dict[str, str] = {}
    for q_id, (title, _badge, question) in PERCEPTION_QUESTIONS.items():
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=350,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PERCEPTION,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": question}],
            )
            answers[q_id] = message.content[0].text.strip()
        except Exception as e:
            logger.error(f"AI perception {q_id} failed: {e}")
            answers[q_id] = f"Query failed: {e}"

    # Cache under today's key; keep last 7 days only
    cache = _load_json_cache(AI_PERCEPTION_CACHE)
    cache[cache_key] = answers
    if len(cache) > 7:
        del cache[sorted(cache.keys())[0]]
    _save_json_cache(AI_PERCEPTION_CACHE, cache)
    return answers
