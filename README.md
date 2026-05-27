# External Voice Dashboard — Discount Tire

Executive-grade brand monitoring dashboard that aggregates and analyzes customer reviews from Reddit, Trustpilot, and ConsumerAffairs using AI-powered theme classification and insights.

---

## Features

- **Multi-source aggregation** — Reddit (PRAW), Trustpilot, ConsumerAffairs
- **AI theme classification** — Two-level taxonomy (5 categories, 22 sub-themes) via Claude
- **Executive headline** — Auto-generated 4–5 sentence summary of brand voice
- **10-section dashboard** — Health score, metric cards, split theme charts, deep dive, sentiment, volume trends, rating distribution, reviews feed, AI chat
- **Persistent caching** — Reviews and theme results cached in `cache/` to minimize API calls
- **AI chat assistant** — Ask natural-language questions about your review data

---

## Quick Start

### 1. Clone / navigate to the project

```bash
cd /path/to/external-listening
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` with your real credentials:

```env
ANTHROPIC_API_KEY=sk-ant-...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USERNAME=...
REDDIT_PASSWORD=...
```

**Anthropic API key** — Required for theme classification, insights, and chat. Get one at https://console.anthropic.com.

**Reddit credentials** — Optional. Create an app at https://www.reddit.com/prefs/apps (choose "script"). Reddit data will be skipped if credentials are absent.

### 5. Run the dashboard

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## First Use

1. The dashboard loads **sample data** automatically so you can see the layout
2. Click **"Sync Latest Data"** in the sidebar to fetch real reviews
3. Theme classification runs automatically after sync (uses Claude API)
4. The headline insight and AI chat will activate once `ANTHROPIC_API_KEY` is set

---

## Data Sources

### Reddit (PRAW)
Searches for "Discount Tire" posts and qualifying comments across:
- r/DiscountTire, r/MechanicAdvice, r/TireBuying, r/askcarsales, r/Cartalk

### Trustpilot
Scrapes public reviews from https://www.trustpilot.com/review/www.discounttire.com  
> Note: Trustpilot uses Next.js — the scraper attempts to extract the embedded JSON data blob, then falls back to HTML parsing. If Trustpilot changes their page structure, parsing may return fewer results.

### ConsumerAffairs
Scrapes structured review data from https://www.consumeraffairs.com/automotive/discount-tire.html  
Uses schema.org markup for reliable extraction.

---

## Theme Taxonomy

| Level 1 | Level 2 Sub-themes |
|---|---|
| Quality of Service | Attention to Detail, Speed and Efficiency, Tire Installation, Alignment, Tire Pressure, Wheel, Valve Stem Caps, Incorrect Service, Hubcaps, Spare Tire, TPMS Sensors |
| Customer Service | Professionalism, Knowledge, Loyalty, Recognition |
| Customer Concerns / Feedback | Issue Resolution, Improvement Suggestions, Perceived Upselling |
| Store Environment | Cleanliness, Organization, Atmosphere, Amenities |
| Time | Wait Times, Quoted Inaccurate Wait Time, Appointment Not Honored |

---

## Cache Files

| File | Contents |
|---|---|
| `cache/reviews.json` | Normalised review records |
| `cache/themes_cache.json` | Claude theme classifications keyed by review ID |
| `cache/headline_cache.json` | Daily AI-generated executive headline |
| `cache/theme_summaries.json` | Per-theme AI summaries (cached daily) |

Delete any cache file to force a fresh fetch or re-analysis.

---

## Project Structure

```
external-listening/
├── app.py                          # Main Streamlit application
├── requirements.txt
├── .env.example
├── src/
│   ├── data/
│   │   ├── reddit_collector.py     # PRAW Reddit collection
│   │   ├── trustpilot_scraper.py   # Trustpilot scraping
│   │   ├── consumer_affairs_scraper.py
│   │   └── data_manager.py         # Normalisation, caching, sample data
│   ├── analysis/
│   │   ├── theme_classifier.py     # Claude-powered theme analysis
│   │   └── ai_insights.py          # Headline, theme summaries, chat
│   └── ui/
│       ├── styles.py               # Dark theme CSS
│       └── charts.py               # Plotly chart builders
└── cache/                          # Auto-created on first sync
```

---

## Troubleshooting

**"No reviews found on Trustpilot"** — Trustpilot may have updated their HTML structure. The scraper tries the Next.js JSON blob first; if that fails, it falls back to BeautifulSoup. Check for anti-bot headers in the network tab.

**Theme analysis is slow** — Classification batches 20 comments per API call. A large initial sync of 200+ reviews may take 1–2 minutes. Results are cached permanently.

**Reddit returns 0 posts** — Verify `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and that the Reddit app type is "script".

**"ANTHROPIC_API_KEY not set"** — The dashboard renders with cached data but AI features (insights, theme classification, chat) are disabled until the key is added to `.env`.

---

## Costs

Theme classification uses `claude-sonnet-4-6` with prompt caching. For 500 reviews, expect ~$0.10–0.20 in API costs on first analysis. Subsequent syncs only re-classify new reviews. The daily headline and chat use ~$0.001–0.005 per call.
