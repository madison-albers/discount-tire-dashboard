import hashlib
import html as _html_mod
import logging
import os
import re

import pandas as pd

logger = logging.getLogger(__name__)

REVIEWS_CACHE = "cache/reviews.json"

# Compiled once for performance
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE  = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    """Strip HTML tags, decode entities, and normalise whitespace."""
    if not isinstance(text, str) or not text:
        return text or ""
    text = _html_mod.unescape(text)         # &amp; → &, &#39; → ', etc.
    text = _TAG_RE.sub(" ", text)           # <p class="review-quote"> → space
    text = _WS_RE.sub(" ", text).strip()    # collapse runs of spaces/newlines
    return text


def _make_id(text: str) -> str:
    return hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()[:12]


def normalize_reviews(raw_data: list[dict]) -> pd.DataFrame:
    if not raw_data:
        return pd.DataFrame()

    df = pd.DataFrame(raw_data)

    # Ensure required columns
    for col in ["comment_text", "source", "date", "rating", "url"]:
        if col not in df.columns:
            df[col] = None

    # Clean text: strip HTML tags, decode entities, normalise whitespace
    df["comment_text"] = df["comment_text"].fillna("").apply(_clean_text)
    df = df[df["comment_text"].str.len() >= 20].copy()

    # Stable ID: prefer reddit_id (exact dedup) then fall back to content hash
    if "reddit_id" in df.columns and df["reddit_id"].notna().any():
        df["id"] = df["reddit_id"].where(
            df["reddit_id"].notna(),
            df["comment_text"].apply(_make_id),
        )
    else:
        df["id"] = df["comment_text"].apply(_make_id)

    # Normalise dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df["date"] = df["date"].dt.tz_localize(None)

    # Normalise ratings
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df.loc[df["rating"] < 1, "rating"] = None
    df.loc[df["rating"] > 5, "rating"] = None

    # Drop duplicates on id
    df = df.drop_duplicates(subset=["id"]).reset_index(drop=True)

    # Fill optional columns with None if missing
    for col in ["level1", "level2", "sentiment",
                "item_type", "post_title", "comment_author", "upvotes"]:
        if col not in df.columns:
            df[col] = None

    logger.info(f"Normalised {len(df)} reviews")
    return df


def save_reviews(df: pd.DataFrame) -> None:
    os.makedirs("cache", exist_ok=True)
    df_copy = df.copy()
    if "date" in df_copy.columns:
        df_copy["date"] = df_copy["date"].astype(str)
    df_copy.to_json(REVIEWS_CACHE, orient="records", date_format="iso", indent=2)


def load_reviews() -> pd.DataFrame:
    if not os.path.exists(REVIEWS_CACHE):
        return pd.DataFrame()
    try:
        df = pd.read_json(REVIEWS_CACHE, orient="records")
        if df.empty:
            return df
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        # Re-apply HTML cleaning in case old cached data contains raw tags
        if "comment_text" in df.columns:
            df["comment_text"] = df["comment_text"].fillna("").apply(_clean_text)
        return df
    except Exception as e:
        logger.warning(f"Could not load cache: {e}")
        return pd.DataFrame()


def get_sample_data() -> pd.DataFrame:
    """Return a small demo dataset when no real data is available."""
    sample = [
        {
            "id": "demo001",
            "comment_text": "Great service at Discount Tire! They rotated my tires quickly and the staff was very professional.",
            "source": "Trustpilot",
            "date": "2024-03-15",
            "rating": 5,
            "url": "https://www.trustpilot.com/review/www.discounttire.com",
            "level1": "Customer Service",
            "level2": "Professionalism",
            "sentiment": "positive",
        },
        {
            "id": "demo002",
            "comment_text": "Waited 2 hours for a simple tire rotation. They quoted 45 minutes. Very disappointed.",
            "source": "ConsumerAffairs",
            "date": "2024-03-10",
            "rating": 2,
            "url": "https://www.consumeraffairs.com/automotive/discount-tire.html",
            "level1": "Time",
            "level2": "Quoted Inaccurate Wait Time",
            "sentiment": "negative",
        },
        {
            "id": "demo003",
            "comment_text": "I've been going to Discount Tire for 10 years. Always reliable and honest pricing.",
            "source": "Trustpilot",
            "date": "2024-02-28",
            "rating": 5,
            "url": "https://www.trustpilot.com/review/www.discounttire.com",
            "level1": "Customer Service",
            "level2": "Loyalty",
            "sentiment": "positive",
        },
        {
            "id": "demo004",
            "comment_text": "They tried to upsell me on road hazard protection multiple times when I said no. Felt pushy.",
            "source": "Reddit",
            "date": "2024-02-20",
            "rating": None,
            "url": "https://reddit.com/r/MechanicAdvice",
            "level1": "Customer Concerns / Feedback",
            "level2": "Perceived Upselling",
            "sentiment": "negative",
        },
        {
            "id": "demo005",
            "comment_text": "The technician named Marcus did an excellent job. Noticed my valve stem was cracked and fixed it.",
            "source": "ConsumerAffairs",
            "date": "2024-02-15",
            "rating": 5,
            "url": "https://www.consumeraffairs.com/automotive/discount-tire.html",
            "level1": "Customer Service",
            "level2": "Recognition",
            "sentiment": "positive",
        },
        {
            "id": "demo006",
            "comment_text": "TPMS sensor wasn't properly reset after tire change. Had to come back twice.",
            "source": "Reddit",
            "date": "2024-02-10",
            "rating": None,
            "url": "https://reddit.com/r/TireBuying",
            "level1": "Quality of Service",
            "level2": "TPMS Sensors",
            "sentiment": "negative",
        },
        {
            "id": "demo007",
            "comment_text": "The waiting room was clean and comfortable. They have coffee and WiFi. Made the wait pleasant.",
            "source": "Trustpilot",
            "date": "2024-01-30",
            "rating": 4,
            "url": "https://www.trustpilot.com/review/www.discounttire.com",
            "level1": "Store Environment",
            "level2": "Amenities",
            "sentiment": "positive",
        },
        {
            "id": "demo008",
            "comment_text": "They installed the wrong size tires and I didn't notice until I got home. Had to waste another trip.",
            "source": "ConsumerAffairs",
            "date": "2024-01-22",
            "rating": 1,
            "url": "https://www.consumeraffairs.com/automotive/discount-tire.html",
            "level1": "Quality of Service",
            "level2": "Incorrect Service",
            "sentiment": "negative",
        },
        {
            "id": "demo009",
            "comment_text": "Great prices, fast installation, and they checked my spare tire too without being asked. Impressive.",
            "source": "Reddit",
            "date": "2024-01-18",
            "rating": None,
            "url": "https://reddit.com/r/Cartalk",
            "level1": "Quality of Service",
            "level2": "Speed and Efficiency",
            "sentiment": "positive",
        },
        {
            "id": "demo010",
            "comment_text": "Staff knew exactly what tire would work best for my commute and budget. Super knowledgeable team.",
            "source": "Trustpilot",
            "date": "2024-01-05",
            "rating": 5,
            "url": "https://www.trustpilot.com/review/www.discounttire.com",
            "level1": "Customer Service",
            "level2": "Knowledge",
            "sentiment": "positive",
        },
        {
            "id": "demo011",
            "comment_text": "Had an appointment at 10am, didn't get my car back until noon. Appointments seem pointless.",
            "source": "ConsumerAffairs",
            "date": "2023-12-28",
            "rating": 2,
            "url": "https://www.consumeraffairs.com/automotive/discount-tire.html",
            "level1": "Time",
            "level2": "Appointment Not Honored",
            "sentiment": "negative",
        },
        {
            "id": "demo012",
            "comment_text": "They damaged my hubcap during installation and denied it. Never going back.",
            "source": "Reddit",
            "date": "2023-12-15",
            "rating": None,
            "url": "https://reddit.com/r/askcarsales",
            "level1": "Quality of Service",
            "level2": "Hubcaps",
            "sentiment": "negative",
        },
        {
            "id": "demo013",
            "comment_text": "Price matched a competitor without me even asking. That's good business.",
            "source": "Trustpilot",
            "date": "2023-12-10",
            "rating": 5,
            "url": "https://www.trustpilot.com/review/www.discounttire.com",
            "level1": "Customer Service",
            "level2": "Professionalism",
            "sentiment": "positive",
        },
        {
            "id": "demo014",
            "comment_text": "Wish they offered online check-in to reduce wait times. The walk-in process is slow.",
            "source": "ConsumerAffairs",
            "date": "2023-12-01",
            "rating": 3,
            "url": "https://www.consumeraffairs.com/automotive/discount-tire.html",
            "level1": "Customer Concerns / Feedback",
            "level2": "Improvement Suggestions",
            "sentiment": "neutral",
        },
        {
            "id": "demo015",
            "comment_text": "Tire pressure was uneven after install — two tires were at 38 psi and two at 32.",
            "source": "Reddit",
            "date": "2023-11-20",
            "rating": None,
            "url": "https://reddit.com/r/MechanicAdvice",
            "level1": "Quality of Service",
            "level2": "Tire Pressure",
            "sentiment": "negative",
        },
    ]

    df = pd.DataFrame(sample)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df
