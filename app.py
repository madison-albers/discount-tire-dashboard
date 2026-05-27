"""
External Voice Dashboard — Discount Tire
Monitors brand presence on Reddit. Themes classified by Claude AI.
"""

import html as _html
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ── Path + env ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()
logging.basicConfig(level=logging.INFO)

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="External Voice Dashboard — Discount Tire",
    page_icon="🔵",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.ui.styles import CUSTOM_CSS
from src.ui.charts import (
    theme_bar_chart,
    volume_trend_chart,
    rating_distribution_chart,
    sentiment_donut,
    sparkline,
)
from src.data.data_manager import load_reviews, save_reviews, normalize_reviews
from src.analysis.theme_classifier import analyze_themes_batch
from src.analysis.ai_insights import (
    generate_headline_insight,
    generate_theme_summary,
    chat_with_reviews,
    fetch_ai_perception,
    PERCEPTION_QUESTIONS,
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "authenticated":      False,
        "df":                 pd.DataFrame(),
        "chat_history":       [],
        "show_more":          False,
        "last_sync":          None,
        "headline":           None,
        "reddit_status":      None,   # {"ok": bool, "count": int, "error": str}
        "refresh_perception": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── Login gate ────────────────────────────────────────────────────────────────
def _show_login():
    st.markdown("""
    <style>
    .login-card {
        background: #1A1D2E;
        border: 1px solid #2A2D3E;
        border-radius: 16px;
        padding: 52px 56px 48px;
        box-shadow: 0 8px 40px rgba(0,0,0,0.5);
        text-align: center;
    }
    .login-logo {
        font-size: 13px; font-weight: 800; color: #4F8EF7;
        letter-spacing: 3px; text-transform: uppercase;
        border: 2px solid #4F8EF7; padding: 7px 18px;
        border-radius: 6px; display: inline-block; margin-bottom: 28px;
    }
    .login-title {
        font-size: 22px; font-weight: 700; color: #FFFFFF !important;
        margin-bottom: 6px;
    }
    .login-subtitle {
        font-size: 13px; color: #8B8FA8 !important; margin-bottom: 36px;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
        <div style="padding:80px 0 28px">
          <div class="login-logo">🔵 DISCOUNT TIRE</div>
          <div class="login-title">External Voice Dashboard</div>
          <div class="login-subtitle">Brand intelligence · Powered by Claude AI</div>
        </div>""", unsafe_allow_html=True)

        with st.container():
            pwd = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password",
                key="login_pwd",
                label_visibility="collapsed",
            )
            if st.button("Sign In →", type="primary", use_container_width=True, key="login_btn"):
                correct = os.getenv("DASHBOARD_PASSWORD", "")
                if pwd == correct:
                    st.session_state.authenticated = True
                    st.rerun()
                elif not correct:
                    st.error("DASHBOARD_PASSWORD is not set in .env")
                else:
                    st.error("Incorrect password")


if not st.session_state.authenticated:
    _show_login()
    st.stop()


# ── Data helpers ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def _cached_load() -> pd.DataFrame:
    return load_reviews()


def _merge_themes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    already = df["level1"].notna().sum() if "level1" in df.columns else 0
    if already == len(df):
        return df
    with st.spinner("Classifying themes with AI…"):
        comments   = df[["id", "comment_text", "rating"]].to_dict(orient="records")
        theme_map  = analyze_themes_batch(comments)
    df = df.copy()
    df["level1"]    = df["id"].map(lambda x: theme_map.get(x, {}).get("level1", "Quality of Service"))
    df["level2"]    = df["id"].map(lambda x: theme_map.get(x, {}).get("level2", "Attention to Detail"))
    df["sentiment"] = df["id"].map(lambda x: theme_map.get(x, {}).get("sentiment", "neutral"))
    return df


def _sync_data():
    """Fetch Reddit data, classify themes, persist to cache."""
    progress = st.progress(0, text="Connecting to Reddit…")

    # ── Reddit (only live source) ─────────────────────────────────────────────
    # Additional data sources (Trustpilot, ConsumerAffairs, Yelp, BBB, Google)
    # can be added here once scrapers are available.
    if not os.getenv("REDDIT_CLIENT_ID"):
        st.session_state.reddit_status = {"ok": False, "count": 0,
                                           "error": "REDDIT_CLIENT_ID not set in .env"}
        progress.empty()
        st.error("Reddit credentials missing — add REDDIT_CLIENT_ID to .env")
        return

    try:
        from src.data.reddit_collector import fetch_reddit_data
        items = fetch_reddit_data(limit=100)
        st.session_state.reddit_status = {"ok": True, "count": len(items), "error": ""}
        st.toast(f"✅ Reddit: {len(items)} posts fetched", icon="✅")
    except Exception as e:
        st.session_state.reddit_status = {"ok": False, "count": 0, "error": str(e)[:120]}
        progress.empty()
        st.error(f"Reddit fetch failed: {e}")
        return

    progress.progress(50, text="Classifying themes…")

    if items:
        df = normalize_reviews(items)
        df = _merge_themes(df)
        save_reviews(df)
        st.session_state.df         = df
        st.session_state.last_sync  = datetime.now()
        st.session_state.headline   = None
        st.cache_data.clear()
        progress.progress(100, text="Done.")
        st.success(f"Synced {len(df):,} Reddit posts.")
        st.rerun()
    else:
        progress.empty()
        st.warning("Reddit returned 0 results. Check credentials and subreddit access.")


# ── Load on first run ─────────────────────────────────────────────────────────
if st.session_state.df.empty:
    cached = _cached_load()
    if not cached.empty:
        st.session_state.df = cached


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="logo-box">🔵 DISCOUNT TIRE</div>', unsafe_allow_html=True)

    if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("### Filters")

    df_all = st.session_state.df

    # Date range
    default_from = datetime.now() - timedelta(days=180)
    c1, c2 = st.columns(2)
    with c1:
        date_from = st.date_input("From", value=default_from.date(), key="sb_from")
    with c2:
        date_to = st.date_input("To", value=datetime.now().date(), key="sb_to")

    # Sentiment
    sel_sentiment = st.multiselect(
        "Sentiment", ["positive", "neutral", "negative"],
        default=["positive", "neutral", "negative"], key="sb_sent",
    )

    # Level 1 category
    cat_opts = ["All"]
    if not df_all.empty and "level1" in df_all.columns:
        cat_opts += sorted(df_all["level1"].dropna().unique().tolist())
    sel_cat = st.selectbox("Category", cat_opts, key="sb_cat")

    st.divider()

    if st.button("🔄  Sync Latest Data", type="primary", use_container_width=True):
        _sync_data()

    if st.button("🧠  Re-analyze Themes", use_container_width=True):
        if not st.session_state.df.empty:
            st.session_state.df = _merge_themes(st.session_state.df)
            save_reviews(st.session_state.df)
            st.session_state.headline = None
            st.cache_data.clear()
            st.rerun()

    if st.button("📊  Export to Excel", use_container_width=True):
        if not st.session_state.df.empty:
            out = "cache/reviews_export.xlsx"
            exp = st.session_state.df.copy()
            if "date" in exp.columns:
                exp["date"] = exp["date"].astype(str)
            exp.to_excel(out, index=False)
            with open(out, "rb") as fh:
                st.download_button(
                    "⬇️ Download",
                    fh,
                    file_name=f"dt_reddit_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    # ── Data source status ────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Data sources**")
    rs = st.session_state.reddit_status
    if rs is None:
        if not st.session_state.df.empty:
            st.caption(f"✅ Reddit · {len(st.session_state.df):,} posts loaded from cache")
        else:
            st.caption("⬜ Reddit — click Sync to fetch")
    elif rs["ok"]:
        st.caption(f"✅ Reddit · {rs['count']:,} posts")
    else:
        st.warning(f"Reddit unavailable: {rs['error'][:60]}", icon="⚠️")


# ══════════════════════════════════════════════════════════════════════════════
# APPLY FILTERS
# ══════════════════════════════════════════════════════════════════════════════
df = st.session_state.df.copy()

if not df.empty:
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df[(df["date"].dt.date >= date_from) & (df["date"].dt.date <= date_to)]

    if sel_sentiment and "sentiment" in df.columns:
        df = df[df["sentiment"].isin(sel_sentiment)]

    if sel_cat != "All" and "level1" in df.columns:
        df = df[df["level1"] == sel_cat]


# ── Utility helpers ───────────────────────────────────────────────────────────

def _health(d: pd.DataFrame) -> int:
    if d.empty or "sentiment" not in d.columns or d["sentiment"].isna().all():
        return 0
    return round((d["sentiment"] == "positive").sum() / len(d) * 100)


def _stars(n) -> str:
    try:
        return "★" * int(n)
    except Exception:
        return ""


def _sentiment_badge(s: str) -> str:
    cls  = {"positive": "badge-pos", "negative": "badge-neg", "neutral": "badge-neu"}.get(s, "badge-neu")
    icon = {"positive": "↑", "negative": "↓", "neutral": "→"}.get(s, "→")
    return f'<span class="badge {cls}">{icon} {s.capitalize()}</span>'


def _safe(text: str) -> str:
    """Escape text for safe embedding inside an HTML template string.

    Prevents raw HTML tags in comment_text from breaking card layout
    even if data_manager._clean_text missed something.
    """
    return _html.escape(str(text), quote=False)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — HEADER BAR
# ══════════════════════════════════════════════════════════════════════════════
health = _health(df)
hcls   = "health-pos" if health >= 60 else ("health-mid" if health >= 40 else "health-neg")
icon   = "●" if health >= 60 else ("◑" if health >= 40 else "○")
sync_ts = (
    st.session_state.last_sync.strftime("%b %d, %Y %I:%M %p")
    if st.session_state.last_sync else "Not synced"
)

st.markdown(f"""
<div class="dash-header">
  <div>
    <div class="dash-title">Discount Tire — External Voice Dashboard</div>
    <div class="dash-subtitle">Reddit brand intelligence · Themes classified by Claude AI</div>
  </div>
  <div class="health-block">
    <div class="health-label">Reddit Health Score</div>
    <div class="health-value {hcls}">{icon} {health}%</div>
    <div class="health-ts">Last synced: {sync_ts}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — AI HEADLINE INSIGHT
# ══════════════════════════════════════════════════════════════════════════════
if not df.empty:
    if st.session_state.headline is None:
        st.session_state.headline = generate_headline_insight(df)
    insight = st.session_state.headline or ""
    st.markdown(f"""
    <div class="insight-box">
      <div class="insight-heading">✦ Executive Insight — Reddit</div>
      <div class="insight-text">{insight}</div>
      <div class="ai-badge">Generated by Claude AI · Based on Reddit data</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info(
        "No Reddit data loaded. Click **Sync Latest Data** in the sidebar to fetch posts.",
        icon="ℹ️",
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — METRIC CARDS
# ══════════════════════════════════════════════════════════════════════════════
total       = len(df)
pct_pos     = health
top_complaint = "—"
if not df.empty and "sentiment" in df.columns and "level2" in df.columns:
    neg = df[df["sentiment"] == "negative"]
    if not neg.empty and neg["level2"].notna().any():
        top_complaint = neg["level2"].value_counts().index[0]

pos_color = "#4F8EF7" if pct_pos >= 60 else ("#F7B731" if pct_pos >= 40 else "#F75C5C")
pos_trend = "↑ Positive lean" if pct_pos >= 60 else ("→ Mixed" if pct_pos >= 40 else "↓ Needs attention")

# Subreddit count
n_subs = 0
if not df.empty and "subreddit" in df.columns:
    n_subs = df["subreddit"].nunique()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-icon">📊</div>
      <div class="metric-label">Total Posts</div>
      <div class="metric-value">{total:,}</div>
      <div class="metric-trend t-mid">Reddit posts &amp; comments</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-icon">🗂️</div>
      <div class="metric-label">Subreddits</div>
      <div class="metric-value">{n_subs}</div>
      <div class="metric-trend t-mid">Communities monitored</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-icon">💬</div>
      <div class="metric-label">% Positive Sentiment</div>
      <div class="metric-value" style="color:{pos_color}">{pct_pos}%</div>
      <div class="metric-trend {'t-up' if pct_pos>=60 else ('t-mid' if pct_pos>=40 else 't-down')}">{pos_trend}</div>
    </div>""", unsafe_allow_html=True)

with col4:
    val_cls = "metric-value-sm" if len(top_complaint) > 12 else "metric-value"
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-icon">⚠️</div>
      <div class="metric-label">Top Complaint Theme</div>
      <div class="{val_cls}">{top_complaint}</div>
      <div class="metric-trend t-down">Most frequent negative theme</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — THEME CHARTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-hdr">Theme Analysis</div>', unsafe_allow_html=True)

ctrl1, ctrl2 = st.columns([3, 1])
with ctrl1:
    theme_level = st.radio(
        "Level", ["Level 1 — Categories", "Level 2 — Sub-themes"],
        horizontal=True, label_visibility="collapsed", key="theme_level",
    )

theme_col = "level2" if "Level 2" in theme_level else "level1"
left, right = st.columns(2)

with left:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    if not df.empty and "sentiment" in df.columns and theme_col in df.columns:
        pos_df = df[df["sentiment"] == "positive"]
        if not pos_df.empty and pos_df[theme_col].notna().any():
            pos_counts = pos_df[theme_col].value_counts()
            # % of positive comments — each bar = share within positives
            pos_pct = (pos_counts / len(pos_df) * 100).head(10).to_dict()
            st.plotly_chart(
                theme_bar_chart(pos_pct, "What Customers Love", "#4F8EF7", height=380),
                use_container_width=True, config={"displayModeBar": False},
            )
        else:
            st.info("No positive reviews in current filter.")
    else:
        st.info("Sync data to see theme charts.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    if not df.empty and "sentiment" in df.columns and theme_col in df.columns:
        neg_df = df[df["sentiment"] == "negative"]
        if not neg_df.empty and neg_df[theme_col].notna().any():
            neg_counts = neg_df[theme_col].value_counts()
            neg_pct    = (neg_counts / len(neg_df) * 100).head(10).to_dict()
            st.plotly_chart(
                theme_bar_chart(neg_pct, "What Customers Complain About", "#F75C5C", height=380),
                use_container_width=True, config={"displayModeBar": False},
            )
        else:
            st.info("No negative reviews in current filter.")
    else:
        st.info("Sync data to see complaint themes.")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — THEME DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════════
PREVIEW_LEN = 300   # shared constant; also used by Recent Reviews feed

st.markdown('<div class="section-hdr">Theme Deep Dive</div>', unsafe_allow_html=True)

if not df.empty and "level2" in df.columns and df["level2"].notna().any():
    theme_choices = sorted(df["level2"].dropna().unique().tolist())
    sel_theme = st.selectbox("Explore theme", theme_choices, key="dd_theme")

    if sel_theme:
        theme_df = df[df["level2"] == sel_theme].copy()
        if "date" in theme_df.columns:
            theme_df["date"] = pd.to_datetime(theme_df["date"], errors="coerce")
            theme_df = theme_df.sort_values("date", ascending=False)

        n_posts    = (theme_df.get("item_type", pd.Series()) == "post").sum()
        n_comments = (theme_df.get("item_type", pd.Series()) == "comment").sum()
        count_label = (
            f"{n_posts} posts and {n_comments} comments"
            if "item_type" in theme_df.columns
            else f"{len(theme_df)} items"
        )

        # AI summary + charts live above the item list
        col_left, col_right = st.columns([3, 2])
        with col_left:
            ai_summary = generate_theme_summary(
                sel_theme, theme_df["comment_text"].head(15).tolist()
            )
            st.markdown(f"""
            <div style="background:rgba(79,142,247,0.06);border-left:3px solid #4F8EF7;
                        padding:12px 16px;border-radius:0 8px 8px 0;margin-bottom:14px;">
              <p style="color:#C4C8D8;font-size:13px;line-height:1.7;margin:0">{ai_summary}</p>
            </div>""", unsafe_allow_html=True)
        with col_right:
            fig_donut = sentiment_donut(theme_df)
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
            fig_spark = sparkline(theme_df, "#4F8EF7", height=70)
            if fig_spark.data:
                st.markdown("<div style='margin-top:-6px'><small style='color:#8B8FA8'>Volume trend</small></div>", unsafe_allow_html=True)
                st.plotly_chart(fig_spark, use_container_width=True, config={"displayModeBar": False})

        # All items for this theme
        st.markdown(
            f"<div class='section-hdr' style='font-size:14px;margin-top:12px'>"
            f"{count_label} about <em>{sel_theme}</em></div>",
            unsafe_allow_html=True,
        )

        for _, row in theme_df.iterrows():
            sub        = str(row.get("subreddit", "")).strip()
            dt         = row.get("date")
            ds         = pd.to_datetime(dt).strftime("%b %d, %Y") if pd.notna(dt) else "—"
            text       = str(row.get("comment_text", ""))
            url        = str(row.get("url", ""))
            sent       = row.get("sentiment", "neutral")
            itype      = str(row.get("item_type") or "post")
            post_title = str(row.get("post_title") or "")

            sub_html   = f'<span class="badge badge-sub">r/{sub}</span>' if sub else ""
            itype_icon = "📝" if itype == "post" else "💬"
            itype_html = (
                f'<span style="font-size:11px;color:#8B8FA8">{itype_icon} {itype.capitalize()}</span>'
            )
            link_html  = (
                f'<a href="{url}" target="_blank" style="font-size:11px;color:#8B8FA8;'
                f'text-decoration:none;margin-left:auto">↗ Reddit</a>'
                if url else ""
            )
            parent_html = (
                f'<div style="font-size:11px;color:#8B8FA8;margin-top:4px;font-style:italic">'
                f'Re: {post_title[:80]}{"…" if len(post_title)>80 else ""}</div>'
                if itype == "comment" and post_title else ""
            )

            preview  = _safe(text[:PREVIEW_LEN])
            safe_full = _safe(text)
            has_more = len(text) > PREVIEW_LEN

            st.markdown(f"""
            <div class="review-card">
              <div class="review-meta">
                {sub_html} {itype_html} {_sentiment_badge(sent)}
                <span class="review-date">{ds}</span>
                {link_html}
              </div>
              {parent_html}
              <p class="review-quote">"{preview}{'…' if has_more else ''}"</p>
            </div>""", unsafe_allow_html=True)

            if has_more:
                with st.expander(f"Read full {itype}", expanded=False):
                    st.markdown(
                        f'<p style="font-size:13px;color:#C4C8D8;line-height:1.7;'
                        f'white-space:pre-wrap">{safe_full}</p>',
                        unsafe_allow_html=True,
                    )
                    if url:
                        st.markdown(
                            f'<a href="{url}" target="_blank" style="font-size:12px;'
                            f'color:#4F8EF7">↗ Open on Reddit</a>',
                            unsafe_allow_html=True,
                        )

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — COMPETITOR CO-MENTIONS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-hdr">🏆 Competitor Co-Mentions on Reddit</div>', unsafe_allow_html=True)
st.markdown(
    '<p style="font-size:12px;color:#8B8FA8;margin:-10px 0 12px">How often competitors are '
    'mentioned alongside Discount Tire — bar color reflects whether the context favours '
    'Discount Tire (green) or the competitor (red).</p>',
    unsafe_allow_html=True,
)

# ── Competitor config ─────────────────────────────────────────────────────────
# Each entry: name, match terms, proximity flag (warehouse clubs need tire context)
_COMP_CONFIG: list[dict] = [
    {
        "name":       "Costco Tire Center",
        "terms":      ["costco"],
        "proximity":  True,
        "tire_terms": ["tire", "tires", "wheel", "wheels", "rotation", "auto"],
    },
    {
        "name":       "Sam's Club Tire",
        "terms":      ["sam's club", "sams club"],
        "proximity":  True,
        "tire_terms": ["tire", "tires", "wheel", "wheels", "rotation", "auto"],
    },
    {
        "name":       "Walmart Auto Care",
        "terms":      ["walmart", "wal-mart"],
        "proximity":  True,
        "tire_terms": ["tire", "tires", "auto care", "auto center", "wheel", "wheels"],
    },
    {"name": "Firestone",           "terms": ["firestone"],                                    "proximity": False},
    {"name": "Goodyear",            "terms": ["goodyear"],                                     "proximity": False},
    {"name": "Pep Boys",            "terms": ["pep boys", "pepboys"],                          "proximity": False},
    {"name": "NTB",                 "terms": ["ntb", "national tire"],                         "proximity": False},
    {"name": "Mavis Discount Tire", "terms": ["mavis"],                                        "proximity": False},
    {"name": "America's Tire",      "terms": ["america's tire", "americas tire"],              "proximity": False},
]


def _has_tire_context(text: str, brand_terms: list[str], tire_terms: list[str], window: int = 50) -> bool:
    """True if any brand term appears within `window` words of any tire term."""
    words = text.split()
    n = len(words)
    for brand in brand_terms:
        bw = brand.split()
        blen = len(bw)
        for i in range(n - blen + 1):
            if words[i:i + blen] == bw:
                start = max(0, i - window)
                end   = min(n, i + window + blen)
                ctx   = " ".join(words[start:end])
                if any(t in ctx for t in tire_terms):
                    return True
    return False


def _comp_match(lower_text: str, cfg: dict) -> bool:
    """True if text matches this competitor's criteria (with proximity check if required)."""
    if not any(t in lower_text for t in cfg["terms"]):
        return False
    if cfg.get("proximity"):
        return _has_tire_context(lower_text, cfg["terms"], cfg.get("tire_terms", []))
    return True


def _excerpt(text: str, terms: list[str], width: int = 130) -> str:
    """Short excerpt centred on the first matching term."""
    lower = text.lower()
    for t in terms:
        idx = lower.find(t)
        if idx == -1:
            continue
        start = max(0, idx - 55)
        end   = min(len(text), idx + max(len(t), 75))
        snip  = text[start:end].strip()
        return ("…" if start > 0 else "") + snip + ("…" if end < len(text) else "")
    return text[:width] + ("…" if len(text) > width else "")


# ── Compute per-competitor stats ──────────────────────────────────────────────
if not df.empty and "comment_text" in df.columns:
    comp_rows: list[dict] = []

    for cfg in _COMP_CONFIG:
        mask  = df["comment_text"].str.lower().apply(lambda t: _comp_match(t, cfg))
        sub   = df[mask]
        if sub.empty:
            continue

        # Sentiment mapping: positive → favors DT, negative → favors competitor
        favors_dt   = int((sub.get("sentiment", pd.Series(dtype=str)) == "positive").sum())
        favors_comp = int((sub.get("sentiment", pd.Series(dtype=str)) == "negative").sum())
        neutral     = len(sub) - favors_dt - favors_comp
        total       = len(sub)

        # Best quote: highest-upvoted row that actually contains a competitor term
        best        = sub.sort_values("upvotes", ascending=False).iloc[0]
        quote       = _safe(_excerpt(str(best.get("comment_text", "")), cfg["terms"]))
        quote_url   = str(best.get("url", ""))
        quote_sub   = str(best.get("subreddit", ""))

        comp_rows.append({
            "name":        cfg["name"],
            "total":       total,
            "favors_dt":   favors_dt,
            "favors_comp": favors_comp,
            "neutral":     neutral,
            "quote":       quote,
            "quote_url":   quote_url,
            "quote_sub":   quote_sub,
        })

    comp_rows.sort(key=lambda x: x["total"], reverse=True)

    if comp_rows:
        # ── Build HTML comparison table ───────────────────────────────────────
        def _seg(pct: float, color: str, label: str) -> str:
            if pct < 2:
                return ""
            return (
                f'<div title="{label}" style="width:{pct:.1f}%;background:{color};'
                f'height:100%;display:flex;align-items:center;justify-content:center;'
                f'font-size:9px;color:#fff;font-weight:600;overflow:hidden">'
                f'{"" if pct < 8 else f"{pct:.0f}%"}</div>'
            )

        th = ("padding:8px 14px;text-align:left;font-size:10px;color:#8B8FA8;"
              "font-weight:700;text-transform:uppercase;letter-spacing:0.6px;"
              "border-bottom:1px solid #2A2D3E")
        td = "padding:10px 14px;border-bottom:1px solid #1E2130;vertical-align:middle"

        rows_html = ""
        for r in comp_rows:
            t          = r["total"]
            pct_dt     = r["favors_dt"]   / t * 100
            pct_neu    = r["neutral"]     / t * 100
            pct_comp   = r["favors_comp"] / t * 100
            link_html  = (
                f'<a href="{r["quote_url"]}" target="_blank" '
                f'style="color:#8B8FA8;font-size:10px;text-decoration:none"> ↗</a>'
                if r["quote_url"] else ""
            )
            sub_badge  = (
                f'<span class="badge badge-sub" style="font-size:9px">r/{r["quote_sub"]}</span> '
                if r["quote_sub"] else ""
            )
            lbl_dt   = f"Favors DT: {r['favors_dt']}"
            lbl_neu  = f"Neutral: {r['neutral']}"
            lbl_comp = f"Favors competitor: {r['favors_comp']}"
            bar_html = (
                f'<div style="display:flex;height:18px;border-radius:4px;overflow:hidden;'
                f'background:#2A2D3E;min-width:100px">'
                f'{_seg(pct_dt,   "#4CAF50", lbl_dt)}'
                f'{_seg(pct_neu,  "#F7B731", lbl_neu)}'
                f'{_seg(pct_comp, "#F75C5C", lbl_comp)}'
                f'</div>'
                f'<div style="font-size:10px;color:#8B8FA8;margin-top:3px;white-space:nowrap">'
                f'<span style="color:#4CAF50">✅ {r["favors_dt"]}</span> &nbsp;'
                f'<span style="color:#8B8FA8">⚪ {r["neutral"]}</span> &nbsp;'
                f'<span style="color:#F75C5C">❌ {r["favors_comp"]}</span>'
                f'</div>'
            )

            rows_html += (
                f'<tr>'
                f'<td style="{td}"><span style="font-weight:600;color:#FFFFFF">{r["name"]}</span></td>'
                f'<td style="{td};text-align:center;font-size:20px;font-weight:700;color:#C4C8D8">{t}</td>'
                f'<td style="{td}">{bar_html}</td>'
                f'<td style="{td};font-size:11px;color:#8B8FA8;font-style:italic;max-width:280px">'
                f'{sub_badge}"{r["quote"]}"{link_html}</td>'
                f'</tr>'
            )

        st.markdown(f"""
        <div class="chart-card" style="overflow-x:auto">
          <div style="font-size:11px;color:#8B8FA8;margin-bottom:10px;display:flex;gap:18px">
            <span><span style="color:#4CAF50">■</span> Favors Discount Tire</span>
            <span><span style="color:#F7B731">■</span> Neutral comparison</span>
            <span><span style="color:#F75C5C">■</span> Favors competitor</span>
          </div>
          <table style="width:100%;border-collapse:collapse">
            <thead>
              <tr>
                <th style="{th}">Competitor</th>
                <th style="{th};text-align:center">Mentions</th>
                <th style="{th}">Sentiment Split</th>
                <th style="{th}">Top Example</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("No competitor mentions found. Sync Reddit data to populate.", icon="ℹ️")
else:
    st.info("Sync Reddit data to see competitor analysis.", icon="ℹ️")

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — VOLUME TREND
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-hdr">Volume Trend</div>', unsafe_allow_html=True)
_, vcol = st.columns([5, 1])
with vcol:
    norm_view = st.toggle("% Norm.", value=False, key="vol_norm")

st.markdown('<div class="chart-card">', unsafe_allow_html=True)
st.plotly_chart(volume_trend_chart(df, normalized=norm_view), use_container_width=True, config={"displayModeBar": False})
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — RECENT REDDIT FEED
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-hdr">Recent Reddit Posts &amp; Comments</div>', unsafe_allow_html=True)

# PREVIEW_LEN defined in Section 5 above

show_n = 25 if st.session_state.show_more else 10

if not df.empty:
    feed_df = df.copy()
    if "date" in feed_df.columns:
        feed_df["date"] = pd.to_datetime(feed_df["date"], errors="coerce")
        feed_df = feed_df.sort_values("date", ascending=False)
    recent = feed_df.head(show_n)

    for idx, (_, row) in enumerate(recent.iterrows()):
        sub        = str(row.get("subreddit", "")).strip()
        dt         = row.get("date")
        ds         = pd.to_datetime(dt).strftime("%b %d, %Y") if pd.notna(dt) else "—"
        text       = str(row.get("comment_text", ""))
        url        = str(row.get("url", ""))
        theme      = row.get("level2", "")
        sentiment  = row.get("sentiment", "neutral")
        itype      = str(row.get("item_type") or "post")
        post_title = str(row.get("post_title") or "")

        sub_html   = f'<span class="badge badge-sub">r/{sub}</span>' if sub else ""
        theme_html = (
            f'<span class="badge badge-theme">{theme}</span>'
            if theme and pd.notna(theme) else ""
        )
        itype_icon = "📝" if itype == "post" else "💬"
        itype_html = f'<span style="font-size:11px;color:#8B8FA8">{itype_icon} {itype.capitalize()}</span>'
        link_html  = (
            f'<a href="{url}" target="_blank" style="font-size:11px;color:#8B8FA8;'
            f'text-decoration:none;margin-left:auto">↗ view on Reddit</a>'
            if url else ""
        )
        parent_html = (
            f'<div style="font-size:11px;color:#8B8FA8;margin-top:4px;font-style:italic">'
            f'Re: {post_title[:80]}{"…" if len(post_title)>80 else ""}</div>'
            if itype == "comment" and post_title else ""
        )

        preview   = _safe(text[:PREVIEW_LEN])
        safe_full = _safe(text)
        has_more  = len(text) > PREVIEW_LEN

        st.markdown(f"""
        <div class="review-card">
          <div class="review-meta">
            {sub_html} {itype_html}
            {theme_html}
            {_sentiment_badge(sentiment)}
            <span class="review-date">{ds}</span>
            {link_html}
          </div>
          {parent_html}
          <p class="review-quote">"{preview}{'…' if has_more else ''}"</p>
        </div>""", unsafe_allow_html=True)

        if has_more:
            with st.expander(f"Read full {itype}", expanded=False):
                st.markdown(
                    f'<p style="font-size:13px;color:#C4C8D8;line-height:1.7;'
                    f'white-space:pre-wrap">{safe_full}</p>',
                    unsafe_allow_html=True,
                )
                if url:
                    st.markdown(
                        f'<a href="{url}" target="_blank" style="font-size:12px;color:#4F8EF7">'
                        f'↗ Open original post on Reddit</a>',
                        unsafe_allow_html=True,
                    )

    if len(df) > 10:
        btn_label = "Show fewer ▲" if st.session_state.show_more else "Load more ▼"
        if st.button(btn_label, key="load_more"):
            st.session_state.show_more = not st.session_state.show_more
            st.rerun()
else:
    st.info("No Reddit posts match current filters.", icon="ℹ️")

st.markdown("<br><br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — AI-POWERED PLATFORM INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="perception-wrap">
  <div class="perception-title">🤖 AI-Powered Platform Insights</div>
  <div class="perception-subtitle">How AI perceives Discount Tire across platforms it has seen in training data</div>
</div>""", unsafe_allow_html=True)

# Fetch (optionally re-fetch) perception data
if st.session_state.refresh_perception:
    # Delete cache file so fetch_ai_perception starts fresh
    import json as _json
    cache_path = "cache/ai_perception_cache.json"
    if os.path.exists(cache_path):
        os.remove(cache_path)
    perception_data = fetch_ai_perception(force_refresh=True)
    st.session_state.refresh_perception = False
else:
    perception_data = fetch_ai_perception(force_refresh=False)

# Refresh button
_, btn_col = st.columns([4, 1])
with btn_col:
    if st.button("🔄 Refresh AI Insights", use_container_width=True, key="btn_perception"):
        st.session_state.refresh_perception = True
        st.rerun()

# Render 5 cards in a 2-column grid (3 rows: 2+2+1)
q_items = list(PERCEPTION_QUESTIONS.items())
for row_items in [q_items[0:2], q_items[2:4], q_items[4:5]]:
    cols = st.columns(len(row_items))
    for col, (q_id, (title, badge_cls, question)) in zip(cols, row_items):
        with col:
            answer = perception_data.get(q_id, "Loading…")
            q_short = question[:110] + "…" if len(question) > 110 else question
            st.markdown(f"""
            <div class="perception-card">
              <div class="perception-card-header">
                <span class="badge {badge_cls}">{title}</span>
              </div>
              <div class="perception-q-title">{title}</div>
              <div class="perception-q-text">"{q_short}"</div>
              <div class="perception-divider"></div>
              <div class="perception-answer">{answer}</div>
              <div style="margin-top:12px;font-size:10px;color:#8B8FA8;font-style:italic">
                Based on AI training data — not real-time
              </div>
            </div>""", unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — AI CHAT ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════

# Two rows of suggested questions — Reddit (live data) and external platforms (training data)
_REDDIT_STARTERS = [
    "What do Redditors complain about most?",
    "Which themes are trending negatively on Reddit?",
    "What are customers saying about wait times?",
    "How does Discount Tire compare to competitors on Reddit?",
]
_PLATFORM_STARTERS = [
    "What do Trustpilot reviewers say about Discount Tire?",
    "What are the most common BBB complaints?",
    "How are ConsumerAffairs complaints typically resolved?",
    "What would you recommend Discount Tire focus on?",
]

# ── Chat header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="chat-wrap">
  <div class="chat-title">
    💬 Ask About Discount Tire Customer Feedback
    <span class="chat-powered">Powered by Claude</span>
  </div>
  <div style="font-size:11px;color:#8B8FA8;margin-top:4px">
    Ask about live Reddit data <em>or</em> what customers say on Trustpilot,
    ConsumerAffairs &amp; BBB (from AI training data)
  </div>
</div>""", unsafe_allow_html=True)


# ── Process st.chat_input FIRST ───────────────────────────────────────────────
# Calling st.chat_input before the history render loop ensures that when the
# user submits, the API call completes and the reply is appended to session
# state before the loop below renders — so everything appears in one pass,
# no intermediate st.rerun() required.
user_q = st.chat_input(
    "Ask about Reddit data or what customers say on Trustpilot, ConsumerAffairs, BBB…",
    key="chat_input",
)
if user_q:
    print(f"[Chat UI] question: {user_q[:80]}")
    st.session_state.chat_history.append({"role": "user", "content": user_q})
    with st.spinner("Claude is thinking…"):
        try:
            reply = chat_with_reviews(st.session_state.chat_history, df)
        except Exception as e:
            reply = f"⚠️ Unexpected error: {e}"
            print(f"[Chat UI] error: {e}")
    print(f"[Chat UI] reply ready ({len(reply)} chars)")
    st.session_state.chat_history.append({"role": "assistant", "content": reply})

# ── Starter buttons — only shown when history is empty ───────────────────────
if not st.session_state.chat_history:
    st.markdown(
        "<div style='font-size:11px;color:#8B8FA8;margin:10px 0 5px;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.8px'>Reddit data (live)</div>",
        unsafe_allow_html=True,
    )
    row1_cols = st.columns(4)
    for i, q in enumerate(_REDDIT_STARTERS):
        with row1_cols[i]:
            if st.button(q, key=f"sq_r_{i}", use_container_width=True):
                print(f"[Chat UI] starter: {q[:60]}")
                st.session_state.chat_history.append({"role": "user", "content": q})
                with st.spinner("Claude is thinking…"):
                    try:
                        reply = chat_with_reviews(st.session_state.chat_history, df)
                    except Exception as e:
                        reply = f"⚠️ Unexpected error: {e}"
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

    st.markdown(
        "<div style='font-size:11px;color:#8B8FA8;margin:10px 0 5px;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.8px'>External platforms (AI training data)</div>",
        unsafe_allow_html=True,
    )
    row2_cols = st.columns(4)
    for i, q in enumerate(_PLATFORM_STARTERS):
        with row2_cols[i]:
            if st.button(q, key=f"sq_p_{i}", use_container_width=True):
                print(f"[Chat UI] starter: {q[:60]}")
                st.session_state.chat_history.append({"role": "user", "content": q})
                with st.spinner("Claude is thinking…"):
                    try:
                        reply = chat_with_reviews(st.session_state.chat_history, df)
                    except Exception as e:
                        reply = f"⚠️ Unexpected error: {e}"
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

# ── Render conversation history using st.chat_message ────────────────────────
for msg in st.session_state.chat_history:
    role    = msg["role"]
    content = msg["content"]
    with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
        if content.startswith("⚠️"):
            st.error(content)
        else:
            st.markdown(content)

# ── Clear button ──────────────────────────────────────────────────────────────
if st.session_state.chat_history:
    if st.button("Clear conversation", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
last_updated = (
    st.session_state.last_sync.strftime("%b %d, %Y %I:%M %p")
    if st.session_state.last_sync
    else "not synced"
)
st.markdown(f"""
<div class="dash-footer">
  Data source: <span>Reddit</span> &nbsp;|&nbsp;
  Themes analyzed by <span>Claude AI</span> &nbsp;|&nbsp;
  Last updated: <span>{last_updated}</span>
</div>
""", unsafe_allow_html=True)
