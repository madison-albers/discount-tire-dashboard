CUSTOM_CSS = """
<style>
/* ── Base ── */
.stApp { background-color: #0F1117; }

[data-testid="stSidebar"] {
    background-color: #1A1D2E;
    border-right: 1px solid #2A2D3E;
}

.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

/* ── Typography ── */
h1, h2, h3, h4 { color: #FFFFFF !important; }
p, span, div, label { color: #C4C8D8; }
.stMarkdown p { color: #C4C8D8; }

/* ── Hide Streamlit chrome ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

/* ── Dashboard Header ── */
.dash-header {
    background: linear-gradient(135deg, #1A1D2E 0%, #13162A 100%);
    border: 1px solid #2A2D3E;
    border-radius: 14px;
    padding: 22px 32px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}
.dash-title { font-size: 26px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px; }
.dash-subtitle { font-size: 12px; color: #8B8FA8; margin-top: 4px; }
.health-block { text-align: right; }
.health-label { font-size: 11px; color: #8B8FA8; text-transform: uppercase; letter-spacing: 0.8px; }
.health-value { font-size: 32px; font-weight: 700; line-height: 1; margin-top: 2px; }
.health-pos { color: #4F8EF7; }
.health-mid { color: #F7B731; }
.health-neg { color: #F75C5C; }
.health-ts  { font-size: 11px; color: #8B8FA8; margin-top: 4px; }

/* ── Insight Box ── */
.insight-box {
    background: #1A1D2E;
    border: 1px solid #4F8EF7;
    border-left: 4px solid #4F8EF7;
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 20px;
    box-shadow: 0 4px 24px rgba(79,142,247,0.08);
}
.insight-heading {
    font-size: 11px; font-weight: 700; color: #4F8EF7;
    text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 10px;
}
.insight-text { font-size: 14px; line-height: 1.75; color: #C4C8D8; }
.ai-badge {
    display: inline-block;
    margin-top: 12px;
    background: rgba(79,142,247,0.12);
    color: #4F8EF7;
    font-size: 10px; font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid rgba(79,142,247,0.25);
    letter-spacing: 0.6px;
}

/* ── Metric Cards ── */
.metric-card {
    background: #1A1D2E;
    border: 1px solid #2A2D3E;
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.3);
    transition: border-color 0.2s, transform 0.15s;
    height: 100%;
}
.metric-card:hover { border-color: #4F8EF7; transform: translateY(-2px); }
.metric-icon { font-size: 18px; margin-bottom: 6px; }
.metric-label { font-size: 10px; color: #8B8FA8; text-transform: uppercase; letter-spacing: 0.9px; font-weight: 600; }
.metric-value { font-size: 34px; font-weight: 700; color: #FFFFFF; line-height: 1.1; margin: 3px 0; }
.metric-value-sm { font-size: 22px; font-weight: 700; color: #FFFFFF; line-height: 1.2; margin: 3px 0; }
.metric-trend { font-size: 11px; font-weight: 500; }
.t-up   { color: #4F8EF7; }
.t-down { color: #F75C5C; }
.t-mid  { color: #8B8FA8; }

/* ── Section Headers ── */
.section-hdr {
    font-size: 16px; font-weight: 600; color: #FFFFFF;
    margin: 24px 0 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #2A2D3E;
}

/* ── Chart Cards ── */
.chart-card {
    background: #1A1D2E;
    border: 1px solid #2A2D3E;
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.3);
    margin-bottom: 0;
}

/* ── Review Cards ── */
.review-card {
    background: #1A1D2E;
    border: 1px solid #2A2D3E;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: border-color 0.18s;
}
.review-card:hover { border-color: #4F8EF7; }
.review-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.review-quote { font-size: 13px; color: #C4C8D8; line-height: 1.65; font-style: italic; margin: 0; }
.review-date  { font-size: 11px; color: #8B8FA8; margin-left: auto; }

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 2px 9px; border-radius: 20px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
}
/* Source badges */
.badge-reddit   { background: rgba(255,69,0,0.18); color: #FF6534; border: 1px solid rgba(255,69,0,0.25); }
.badge-theme    { background: rgba(247,183,49,0.12); color: #F7B731; border: 1px solid rgba(247,183,49,0.2); }
.badge-pos      { background: rgba(79,142,247,0.12); color: #4F8EF7; }
.badge-neg      { background: rgba(247,92,92,0.12); color: #F75C5C; }
.badge-neu      { background: rgba(139,143,168,0.12); color: #8B8FA8; }
/* Subreddit badges (same orange family, slight variation) */
.badge-sub      { background: rgba(255,100,40,0.12); color: #FF8A5C; border: 1px solid rgba(255,100,40,0.2); font-size: 10px; }
/* AI Perception platform badges */
.perc-badge-tp      { background: rgba(0,197,94,0.15);   color: #00C55E; border: 1px solid rgba(0,197,94,0.3);   }
.perc-badge-ca      { background: rgba(247,108,26,0.15);  color: #F76C1A; border: 1px solid rgba(247,108,26,0.3); }
.perc-badge-comp    { background: rgba(79,142,247,0.15);  color: #4F8EF7; border: 1px solid rgba(79,142,247,0.3); }
.perc-badge-ratings { background: rgba(247,183,49,0.15);  color: #F7B731; border: 1px solid rgba(247,183,49,0.3); }
.perc-badge-bbb     { background: rgba(180,30,30,0.18);   color: #D44444; border: 1px solid rgba(180,30,30,0.3);  }

/* ── Stars ── */
.stars { color: #F7B731; font-size: 12px; }

/* ── Chat ── */
.chat-wrap {
    background: #1A1D2E;
    border: 1px solid #2A2D3E;
    border-radius: 12px;
    padding: 20px 22px;
    margin-top: 24px;
}
.chat-title {
    font-size: 15px; font-weight: 600; color: #FFFFFF;
    display: flex; align-items: center; gap: 10px; margin-bottom: 16px;
}
.chat-powered {
    font-size: 10px; color: #8B8FA8;
    background: rgba(79,142,247,0.08);
    padding: 2px 8px; border-radius: 10px;
    border: 1px solid rgba(79,142,247,0.18);
}
.msg-user {
    background: rgba(79,142,247,0.12);
    border: 1px solid rgba(79,142,247,0.25);
    border-radius: 12px 12px 4px 12px;
    padding: 10px 14px;
    margin: 6px 0 6px 48px;
    font-size: 13px; color: #C4C8D8;
    line-height: 1.55;
}
.msg-ai {
    background: rgba(26,29,46,0.9);
    border: 1px solid #2A2D3E;
    border-radius: 12px 12px 12px 4px;
    padding: 10px 14px;
    margin: 6px 48px 6px 0;
    font-size: 13px; color: #C4C8D8;
    line-height: 1.65;
}
.starter-q {
    display: inline-block;
    background: rgba(79,142,247,0.08);
    border: 1px solid rgba(79,142,247,0.25);
    color: #4F8EF7;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 12px;
    cursor: pointer;
    margin: 3px 4px 3px 0;
    transition: background 0.15s;
}
.starter-q:hover { background: rgba(79,142,247,0.18); }

/* ── Logo placeholder ── */
.logo-box {
    background: linear-gradient(135deg, #3D6FD9, #2A52A8);
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
    margin-bottom: 20px;
    font-size: 17px; font-weight: 800;
    color: #FFFFFF; letter-spacing: 1px;
    box-shadow: 0 4px 16px rgba(61,111,217,0.3);
}

/* ── AI Perception Monitor ── */
.perception-wrap {
    background: linear-gradient(135deg, #1A1D2E 0%, #141728 100%);
    border: 1px solid #2A2D3E;
    border-top: 3px solid #4F8EF7;
    border-radius: 12px;
    padding: 20px 26px 16px;
    margin-bottom: 20px;
}
.perception-title {
    font-size: 20px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.3px;
}
.perception-subtitle {
    font-size: 12px; color: #8B8FA8; margin-top: 4px;
}
.perception-card {
    background: #1A1D2E;
    border: 1px solid #2A2D3E;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 14px;
    min-height: 180px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
    transition: border-color 0.2s;
}
.perception-card:hover { border-color: #4F8EF7; }
.perception-coming-soon { border-style: dashed; opacity: 0.75; }
.perception-card-header {
    display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
}
.perception-q-title {
    font-size: 13px; font-weight: 700; color: #FFFFFF;
    letter-spacing: -0.1px;
}
.perception-q-text {
    font-size: 11px; color: #8B8FA8; font-style: italic; margin-bottom: 10px; line-height: 1.5;
}
.perception-divider {
    border-top: 1px solid #2A2D3E; margin: 10px 0;
}
.perception-answer {
    font-size: 13px; color: #C4C8D8; line-height: 1.7;
}
.coming-soon-badge {
    display: inline-block;
    background: rgba(139,143,168,0.15);
    color: #8B8FA8;
    font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 10px;
    border: 1px solid rgba(139,143,168,0.25);
    margin-bottom: 10px; letter-spacing: 0.5px;
    text-transform: uppercase;
}
.perception-disclaimer {
    background: rgba(247,183,49,0.06);
    border: 1px solid rgba(247,183,49,0.2);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 11px; color: #8B8FA8;
    margin-top: 8px; line-height: 1.6;
}

/* ── Dashboard footer ── */
.dash-footer {
    text-align: center;
    font-size: 11px; color: #8B8FA8;
    padding: 16px 0 8px;
    border-top: 1px solid #2A2D3E;
    margin-top: 32px;
    letter-spacing: 0.3px;
}
.dash-footer span { color: #4F8EF7; }

/* ── Divider ── */
hr { border-color: #2A2D3E !important; margin: 12px 0 !important; }

/* ── st.chat_message dark-theme overrides ── */
[data-testid="stChatMessage"] {
    background: #1A1D2E !important;
    border: 1px solid #2A2D3E !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    margin-bottom: 8px !important;
}
/* User bubbles — right-side blue tint */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: rgba(79,142,247,0.10) !important;
    border-color: rgba(79,142,247,0.25) !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] td {
    color: #C4C8D8 !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
}
[data-testid="stChatMessage"] strong { color: #FFFFFF !important; }

/* ── Streamlit widget tweaks ── */
.stButton > button {
    border-radius: 8px !important; font-weight: 500 !important;
    transition: all 0.18s !important;
}
.stSelectbox > div > div { background: #1A1D2E !important; border-color: #2A2D3E !important; }
.stMultiSelect > div > div { background: #1A1D2E !important; border-color: #2A2D3E !important; }
.stSlider > div > div { color: #C4C8D8 !important; }
[data-testid="stExpander"] { background: #1A1D2E !important; border-color: #2A2D3E !important; border-radius: 10px !important; }
</style>
"""
