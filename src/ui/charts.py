import plotly.graph_objects as go
import pandas as pd

# ── Palette ──────────────────────────────────────────────────────────────────
C_CARD   = "#1A1D2E"
C_BORDER = "#2A2D3E"
C_TEXT   = "#C4C8D8"
C_DIM    = "#8B8FA8"
C_POS    = "#4F8EF7"   # electric blue
C_NEG    = "#F75C5C"   # coral red
C_GOLD   = "#F7B731"   # gold / neutral
C_REDDIT = "#FF6534"


def _dark_layout(**kwargs) -> dict:
    """Base layout dict for all dark-theme charts.  Pass extra keys via kwargs
    to override or extend — including legend/showlegend when needed."""
    base = dict(
        paper_bgcolor=C_CARD,
        plot_bgcolor=C_CARD,
        font=dict(color=C_TEXT, family="Inter, sans-serif", size=12),
        margin=dict(l=8, r=8, t=36, b=8),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=C_BORDER,
            font=dict(color=C_DIM, size=11),
        ),
    )
    base.update(kwargs)
    return base


# ── Theme horizontal bar charts ───────────────────────────────────────────────

def theme_bar_chart(data: dict, title: str, color: str, height: int = 360) -> go.Figure:
    """Horizontal bar chart showing % per theme, sorted by % descending (largest at top)."""
    if not data:
        return _empty_fig(title, height)

    # Sort descending; autorange="reversed" maps index-0 (largest) to the top
    pairs  = sorted(data.items(), key=lambda x: x[1], reverse=True)
    themes = [p[0] for p in pairs]
    values = [p[1] for p in pairs]
    max_v  = max(values) if values else 1

    r_int = int(color[1:3], 16)
    g_int = int(color[3:5], 16)
    b_int = int(color[5:7], 16)
    bar_colors = [
        f"rgba({r_int},{g_int},{b_int},{0.45 + 0.55*(v/max_v):.2f})"
        for v in values
    ]

    fig = go.Figure(go.Bar(
        x=values,
        y=themes,
        orientation="h",
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        textfont=dict(color=C_DIM, size=11),
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        cliponaxis=False,
    ))

    fig.update_layout(
        **_dark_layout(
            title=dict(text=f"<b>{title}</b>", font=dict(color=C_TEXT, size=13), x=0),
            height=height,
            margin=dict(l=6, r=70, t=40, b=6),
            bargap=0.38,
            showlegend=False,
        )
    )
    fig.update_xaxes(showgrid=False, showticklabels=False, range=[0, max_v * 1.35])
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(color=C_TEXT, size=11))
    return fig


# ── Stacked sentiment bar ─────────────────────────────────────────────────────

def sentiment_stacked_bar(df: pd.DataFrame, height: int = 280) -> go.Figure:
    if df.empty or "source" not in df.columns or "sentiment" not in df.columns:
        return _empty_fig("Sentiment by Source", height)

    sources  = sorted(df["source"].dropna().unique().tolist())
    sent_cfg = [("positive", C_POS), ("neutral", C_GOLD), ("negative", C_NEG)]

    fig = go.Figure()
    for sentiment, color in sent_cfg:
        vals = []
        for src in sources:
            sub   = df[df["source"] == src]
            total = len(sub)
            cnt   = len(sub[sub["sentiment"] == sentiment])
            vals.append((cnt / total * 100) if total else 0)

        fig.add_trace(go.Bar(
            name=sentiment.capitalize(),
            x=sources,
            y=vals,
            marker_color=color,
            text=[f"{v:.0f}%" for v in vals],
            textposition="inside",
            textfont=dict(color="#FFFFFF", size=11),
            hovertemplate=f"{sentiment.capitalize()}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        **_dark_layout(
            height=height,
            barmode="stack",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1,
                bgcolor="rgba(0,0,0,0)", bordercolor=C_BORDER,
                font=dict(color=C_DIM, size=11),
            ),
        )
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color=C_TEXT))
    fig.update_yaxes(showgrid=False, showticklabels=False)
    return fig


# ── Volume trend area chart ───────────────────────────────────────────────────

def volume_trend_chart(df: pd.DataFrame, normalized: bool = False, height: int = 280) -> go.Figure:
    if df.empty or "date" not in df.columns:
        return _empty_fig("Volume Trend", height)

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return _empty_fig("Volume Trend", height)

    df["month"] = df["date"].dt.to_period("M").astype(str)
    fig = go.Figure()

    source_colors = {"Reddit": C_REDDIT}

    for source in sorted(df["source"].dropna().unique()):
        src_df  = df[df["source"] == source]
        monthly = src_df.groupby("month").size().reset_index(name="cnt").sort_values("month")

        if normalized:
            total_by_month = df.groupby("month").size()
            monthly["y"] = monthly.apply(
                lambda r: r["cnt"] / max(total_by_month.get(r["month"], 1), 1) * 100, axis=1
            )
        else:
            monthly["y"] = monthly["cnt"]

        color = source_colors.get(source, C_POS)
        r_c, g_c, b_c = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

        fig.add_trace(go.Scatter(
            x=monthly["month"].tolist(),
            y=monthly["y"].tolist(),
            name=source,
            mode="lines",
            line=dict(color=color, width=2.5, shape="spline", smoothing=0.8),
            fill="tozeroy",
            fillcolor=f"rgba({r_c},{g_c},{b_c},0.12)",
            hovertemplate=f"{source}: %{{y:.1f}}{'%' if normalized else ''}<extra></extra>",
        ))

    fig.update_layout(
        **_dark_layout(
            height=height,
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                bgcolor="rgba(0,0,0,0)", bordercolor=C_BORDER,
                font=dict(color=C_DIM, size=11),
            ),
        )
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color=C_DIM, size=10))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(42,45,62,0.6)", tickfont=dict(color=C_DIM, size=10))
    return fig


# ── Rating distribution ───────────────────────────────────────────────────────

def rating_distribution_chart(df: pd.DataFrame, height: int = 240) -> go.Figure:
    if df.empty or "rating" not in df.columns:
        return _empty_fig("Rating Distribution", height)

    rated = df[df["rating"].notna()]
    if rated.empty:
        return _empty_fig("No rated reviews in current filter", height)

    counts = rated["rating"].value_counts().sort_index()
    total  = len(rated)
    STAR_COLORS = {5: C_POS, 4: "#6BA8FA", 3: C_GOLD, 2: "#F7975C", 1: C_NEG}

    fig = go.Figure()
    for star in [5, 4, 3, 2, 1]:
        cnt = int(counts.get(star, 0))
        pct = cnt / total * 100 if total else 0
        fig.add_trace(go.Bar(
            x=[pct],
            y=[f"{'★' * star}"],
            orientation="h",
            marker_color=STAR_COLORS.get(star, C_DIM),
            showlegend=False,
            text=f"  {cnt}",
            textposition="outside",
            textfont=dict(color=C_DIM, size=11),
            hovertemplate=f"{star}★: {cnt} reviews ({pct:.1f}%)<extra></extra>",
        ))

    fig.update_layout(
        **_dark_layout(
            height=height,
            margin=dict(l=6, r=55, t=36, b=6),
            bargap=0.3,
            showlegend=False,
        )
    )
    fig.update_xaxes(showgrid=False, showticklabels=False, range=[0, 115])
    fig.update_yaxes(showgrid=False, tickfont=dict(color=C_GOLD, size=13))
    return fig


# ── Sentiment donut ───────────────────────────────────────────────────────────

def sentiment_donut(df: pd.DataFrame, height: int = 240) -> go.Figure:
    if df.empty or "sentiment" not in df.columns:
        return _empty_fig("Sentiment", height)

    counts    = df["sentiment"].value_counts()
    color_map = {"positive": C_POS, "neutral": C_GOLD, "negative": C_NEG}

    fig = go.Figure(go.Pie(
        labels=counts.index.tolist(),
        values=counts.values.tolist(),
        hole=0.62,
        marker=dict(
            colors=[color_map.get(s, C_DIM) for s in counts.index],
            line=dict(color=C_CARD, width=2),
        ),
        textinfo="percent",
        textfont=dict(size=11, color=C_TEXT),
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        **_dark_layout(
            height=height,
            margin=dict(l=6, r=6, t=8, b=24),
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="top", y=-0.05,
                xanchor="center", x=0.5,
                bgcolor="rgba(0,0,0,0)", bordercolor=C_BORDER,
                font=dict(color=C_DIM, size=11),
            ),
        )
    )
    return fig


# ── Sparkline ─────────────────────────────────────────────────────────────────

def sparkline(df: pd.DataFrame, color: str, height: int = 80) -> go.Figure:
    if df.empty or "date" not in df.columns:
        return go.Figure()
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return go.Figure()

    period_col = df["date"].dt.to_period("M").astype(str)
    monthly = period_col.value_counts().sort_index().reset_index()
    monthly.columns = ["month", "cnt"]

    r_c, g_c, b_c = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    fig = go.Figure(go.Scatter(
        x=monthly["month"].tolist(),
        y=monthly["cnt"].tolist(),
        mode="lines",
        fill="tozeroy",
        line=dict(color=color, width=1.5, shape="spline"),
        fillcolor=f"rgba({r_c},{g_c},{b_c},0.15)",
        hoverinfo="skip",
    ))
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


# ── Competitor co-mention bar chart ──────────────────────────────────────────

def competitor_chart(competitors: list[dict], height: int = 380) -> go.Figure:
    """
    Horizontal bar chart of competitor co-mention counts.

    Each entry in `competitors`:
        name       str   — competitor display name
        count      int   — number of co-mentions
        color      str   — hex color (green/red/gold based on sentiment context)
        pct_pos    float — fraction of mentions in positive-DT posts (used by caller)
    """
    if not competitors:
        return _empty_fig("No competitor co-mentions found in current data", height)

    # Sort ascending so largest bar appears at top with autorange="reversed"
    comps  = sorted(competitors, key=lambda c: c["count"])
    names  = [c["name"]  for c in comps]
    counts = [c["count"] for c in comps]
    colors = [c["color"] for c in comps]

    fig = go.Figure(go.Bar(
        x=counts,
        y=names,
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[str(n) for n in counts],
        textposition="outside",
        textfont=dict(color=C_DIM, size=12),
        hovertemplate="%{y}: %{x} co-mentions<extra></extra>",
        cliponaxis=False,
    ))

    fig.update_layout(
        **_dark_layout(
            height=height,
            margin=dict(l=8, r=55, t=44, b=8),
            bargap=0.38,
            showlegend=False,
        )
    )
    fig.update_xaxes(showgrid=False, showticklabels=False, range=[0, max(counts) * 1.32])
    fig.update_yaxes(showgrid=False, autorange="reversed",
                     tickfont=dict(color=C_TEXT, size=12))
    return fig


# ── Empty figure ─────────────────────────────────────────────────────────────

def _empty_fig(label: str, height: int = 280) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=height,
        paper_bgcolor=C_CARD,
        plot_bgcolor=C_CARD,
        annotations=[dict(
            text=label,
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=C_DIM, size=13),
        )],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=8, r=8, t=8, b=8),
    )
    return fig
