"""
Reddit data collector.

Collection strategy
───────────────────
r/DiscountTire     — all new posts (limit 500) + all comments 3 levels deep.
                     Posts are included unconditionally (subreddit = brand).
                     Comments are filtered for an explicit DT mention.

SEARCH_SUBREDDITS  — search "Discount Tire" (limit 100 each), strict filter on
                     both posts AND comments (2 levels deep).

r/all search       — search "Discount Tire" across all of Reddit (limit 200),
                     strict filter, top-level comments only.

Deduplication      — by Reddit item ID (post_XXXXX / comment_XXXXX).

Each row contains
──────────────────
comment_text, source, date, rating, url,
subreddit, post_title, comment_author, item_type ("post"|"comment"), upvotes,
reddit_id  (used for dedup / stable id)
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DIRECT_SUBREDDIT = "DiscountTire"

SEARCH_SUBREDDITS = [
    "MechanicAdvice",
    "TireBuying",
    "askcarsales",
    "Cartalk",
    "frugal",
    "personalfinance",
    "cars",
    "autorepair",
    "povertyfinance",
]

SEARCH_QUERY = "Discount Tire"

# Targeted comparison searches — find posts that explicitly pit DT against a
# competitor. Results pass through the same relevance filter as everything else.
COMP_VS_QUERIES = [
    "Costco tires Discount Tire",
    "Sams Club tires Discount Tire",
    "Walmart tires Discount Tire",
    "Firestone vs Discount Tire",
    "Goodyear vs Discount Tire",
]

# Every item (except r/DiscountTire posts) must contain at least one of these.
RELEVANCE_TERMS = (
    "discount tire",
    "discounttire",
    "discount_tire",
    "@discounttire",
)


def _is_relevant(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in RELEVANCE_TERMS)


# ── Item constructors ─────────────────────────────────────────────────────────

def _post_dict(post, subreddit_name: str) -> dict | None:
    try:
        body = f"{post.title}\n{post.selftext}".strip()
        if len(body) < 20:
            return None
        return {
            "reddit_id":      f"post_{post.id}",
            "comment_text":   body,
            "source":         "Reddit",
            "date":           datetime.utcfromtimestamp(post.created_utc).isoformat(),
            "rating":         None,
            "url":            f"https://reddit.com{post.permalink}",
            "subreddit":      subreddit_name,
            "post_title":     post.title,
            "comment_author": str(post.author) if post.author else "[deleted]",
            "item_type":      "post",
            "upvotes":        post.score,
        }
    except Exception as e:
        logger.debug(f"Post dict error: {e}")
        return None


def _comment_dict(comment, post, subreddit_name: str) -> dict | None:
    try:
        body = getattr(comment, "body", "")
        if not body or body in ("[deleted]", "[removed]") or len(body) < 20:
            return None
        return {
            "reddit_id":      f"comment_{comment.id}",
            "comment_text":   body,
            "source":         "Reddit",
            "date":           datetime.utcfromtimestamp(comment.created_utc).isoformat(),
            "rating":         None,
            "url":            f"https://reddit.com{comment.permalink}",
            "subreddit":      subreddit_name,
            "post_title":     post.title,
            "comment_author": str(comment.author) if comment.author else "[deleted]",
            "item_type":      "comment",
            "upvotes":        comment.score,
        }
    except Exception as e:
        logger.debug(f"Comment dict error: {e}")
        return None


# ── Recursive comment walker ──────────────────────────────────────────────────

def _walk_comments(
    comment_forest,
    post,
    subreddit_name: str,
    require_relevance: bool,
    max_depth: int,
    _depth: int = 1,
) -> list[dict]:
    """Recursively collect comments up to max_depth levels."""
    results: list[dict] = []
    if _depth > max_depth:
        return results

    for comment in comment_forest:
        # Skip MoreComments placeholders (no 'body' attribute)
        if not hasattr(comment, "body"):
            continue
        item = _comment_dict(comment, post, subreddit_name)
        if item:
            if (not require_relevance) or _is_relevant(item["comment_text"]):
                results.append(item)
        # Recurse into replies
        if _depth < max_depth:
            try:
                replies = comment.replies
                if replies:
                    results.extend(
                        _walk_comments(
                            replies, post, subreddit_name,
                            require_relevance, max_depth, _depth + 1,
                        )
                    )
            except Exception:
                pass
    return results


# ── Main entry point ──────────────────────────────────────────────────────────

def fetch_reddit_data(limit: int = 500) -> list[dict]:
    try:
        import praw
    except ImportError:
        logger.warning("praw not installed")
        return []

    client_id     = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.info("Reddit credentials not configured")
        return []

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=os.getenv("REDDIT_USERNAME", ""),
            password=os.getenv("REDDIT_PASSWORD", ""),
            user_agent="ExternalVoiceDashboard/1.0",
        )
    except Exception as e:
        logger.error(f"Reddit auth failed: {e}")
        return []

    seen: set[str]     = set()
    results: list[dict] = []
    by_sub: dict[str, int] = {}
    raw_count = 0

    def _add(item: dict | None) -> bool:
        nonlocal raw_count
        if item is None:
            return False
        raw_count += 1
        rid = item["reddit_id"]
        if rid in seen:
            return False
        seen.add(rid)
        results.append(item)
        by_sub[item["subreddit"]] = by_sub.get(item["subreddit"], 0) + 1
        return True

    # ── r/DiscountTire ────────────────────────────────────────────────────────
    try:
        for post in reddit.subreddit(DIRECT_SUBREDDIT).new(limit=limit):
            item = _post_dict(post, DIRECT_SUBREDDIT)
            _add(item)   # All DT posts relevant — no filter

            try:
                post.comments.replace_more(limit=5)
            except Exception:
                pass
            for c_item in _walk_comments(
                post.comments, post, DIRECT_SUBREDDIT,
                require_relevance=True,   # filter comments even in r/DT
                max_depth=3,
            ):
                _add(c_item)
    except Exception as e:
        logger.warning(f"r/{DIRECT_SUBREDDIT}: {e}")

    # ── Search subreddits ─────────────────────────────────────────────────────
    for sub_name in SEARCH_SUBREDDITS:
        try:
            for post in reddit.subreddit(sub_name).search(
                SEARCH_QUERY, limit=min(limit, 100), sort="new"
            ):
                post_body = f"{post.title}\n{post.selftext}"
                if not _is_relevant(post_body):
                    continue

                item = _post_dict(post, sub_name)
                _add(item)

                try:
                    post.comments.replace_more(limit=2)
                except Exception:
                    pass
                for c_item in _walk_comments(
                    post.comments, post, sub_name,
                    require_relevance=True,
                    max_depth=2,
                ):
                    _add(c_item)
        except Exception as e:
            logger.warning(f"r/{sub_name}: {e}")

    # ── r/all broad search ────────────────────────────────────────────────────
    try:
        for post in reddit.subreddit("all").search(
            SEARCH_QUERY, limit=200, sort="new"
        ):
            # Skip subreddits we already covered
            post_sub = post.subreddit.display_name
            if post_sub == DIRECT_SUBREDDIT or post_sub in SEARCH_SUBREDDITS:
                continue

            post_body = f"{post.title}\n{post.selftext}"
            if not _is_relevant(post_body):
                continue

            item = _post_dict(post, post_sub)
            _add(item)

            try:
                post.comments.replace_more(limit=0)
            except Exception:
                pass
            for c_item in _walk_comments(
                post.comments, post, post_sub,
                require_relevance=True,
                max_depth=1,
            ):
                _add(c_item)
    except Exception as e:
        logger.warning(f"r/all search: {e}")

    # ── Targeted competitor comparison searches ───────────────────────────────
    # These queries find posts that explicitly compare DT with a specific
    # competitor — higher signal for the competitor analysis section.
    for query in COMP_VS_QUERIES:
        try:
            for post in reddit.subreddit("all").search(query, limit=100, sort="relevance"):
                post_sub  = post.subreddit.display_name
                post_body = f"{post.title}\n{post.selftext}"
                if not _is_relevant(post_body):
                    continue
                item = _post_dict(post, post_sub)
                _add(item)
                try:
                    post.comments.replace_more(limit=0)
                except Exception:
                    pass
                for c_item in _walk_comments(
                    post.comments, post, post_sub,
                    require_relevance=True, max_depth=1,
                ):
                    _add(c_item)
        except Exception as e:
            logger.warning(f"comp search '{query}': {e}")

    # ── Print summary ─────────────────────────────────────────────────────────
    passed = len(results)
    print(
        f"\n[Reddit] {raw_count} items fetched → "
        f"{passed} passed Discount Tire filter "
        f"({raw_count - passed} filtered out)\n"
        f"[Reddit] Breakdown by subreddit:"
    )
    for sub, n in sorted(by_sub.items(), key=lambda x: x[1], reverse=True):
        print(f"  r/{sub}: {n}")
    print()

    return results
