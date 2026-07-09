# FX Treasury Dashboard — *Why did it move?*

An FX market dashboard that doesn't just show **what** currency pairs are doing — it explains **why** they moved, in plain English, grounded in real news and central‑bank events.

**Live demo**
- App: https://fx-treasury-dashboard.vercel.app
- API: https://fx-treasury-api.onrender.com (docs at `/docs`)

> ⚠️ **Educational tool, not financial advice.** It explains market context; it does not recommend trades.

---

## The problem this solves

FX dashboards are one of the most commoditized products on the internet. TradingView, Investing.com, Myfxbook and every broker give away price charts, heatmaps and “trend” indicators for free. They all answer the same question: **what** is the price doing?

Almost none of them answer the question retail traders and small treasuries actually ask:

> **“Okay… but *why* did it just move?”**

Connecting a price move to the news, rate decision or data release that caused it normally means paying for a Bloomberg terminal or manually cross‑referencing an economic calendar with a news feed. That gap — between *seeing* a move and *understanding* it — is what this project fills.

## What makes it different

When a pair moves, the app:

1. **Detects the real intraday move** from live market data.
2. **Pulls recent, relevant news** for both currencies in the pair (from financial RSS feeds + GDELT), and filters it by whether the *headline* is actually about those currencies — so you get Fed/ECB/RBI and FX stories, not noise.
3. **Generates a one‑sentence, grounded explanation** with an LLM that is only allowed to use the supplied headlines — so it can't invent reasons. If the news doesn't explain the move, it says so.

The result: *“GBP/USD’s move is most likely driven by split opinions among Fed officials on the direction of interest rates…”* — with the source headlines attached.

## Features

- 📈 **FX rate monitor** — live rates, bid/ask/spread, daily % change for major pairs
- 🧠 **“Why did it move?”** — plain‑English, news‑grounded explanations per pair
- 🗞️ **Source transparency** — every explanation links the headlines it used
- 🔔 **Movement alerts** — threshold rules on % moves
- 💼 **Exposure tracker & treasury summary** — payable/receivable positions and notes
- 🕒 **Historical snapshots** — captured on a schedule for trend context

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite, Recharts |
| Backend | FastAPI (Python), SQLAlchemy |
| Database | SQLite (dev) / Postgres (prod‑ready) |
| Market data | [Twelve Data](https://twelvedata.com) (intraday) · [Frankfurter](https://frankfurter.dev) (fallback) |
| News | Financial RSS (ForexLive, CNBC, WSJ) · [GDELT](https://gdeltproject.org) |
| Explanations | Google Gemini (`gemini-2.5-flash`) — Anthropic Claude also supported |
| Hosting | Vercel (frontend) · Render (backend) |

Everything above runs on **free tiers** — no paid data or LLM plan required to get started.

---

## Getting started

### Prerequisites
- Python 3.11+ and Node.js 18+
- Free API keys: [Twelve Data](https://twelvedata.com) and [Google AI Studio (Gemini)](https://aistudio.google.com/apikey)

### 1. Backend (FastAPI)
```bash
cd Backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then edit .env and add your keys
uvicorn app.main:app --reload
```
Backend runs at http://127.0.0.1:8000 (interactive docs at `/docs`).

Set these in `Backend/.env`:
```
MARKET_DATA_PROVIDER=twelvedata
TWELVE_DATA_API_KEY=your_twelvedata_key
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash
FRONTEND_ORIGIN=http://localhost:5173
```
> Prefer no keys at all? Set `MARKET_DATA_PROVIDER=frankfurter` for free daily rates. Explanations still need an LLM key.

### 2. Frontend (React + Vite)
```bash
cd Frontend
npm install
echo "VITE_API_BASE_URL=http://127.0.0.1:8000" > .env
npm run dev
```
Open http://localhost:5173, pick a pair, and click **Explain**.

### 3. Deploy
See [DEPLOY.md](DEPLOY.md) for the full Render + Vercel walkthrough (both free tier).

---

## Key API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/rates/live` | Current rates with bid/ask/spread |
| `GET` | `/rates/latest` | Latest snapshot summary + daily move |
| `GET` | `/explain/{pair}` | **Why the pair moved** (grounded explanation + sources) |
| `GET` | `/rates/history/{pair}` | Historical snapshots for a pair |
| `POST` | `/alerts` | Create a movement alert rule |
| `GET` | `/treasury-summary` | Exposure + FX + alert summary |

Example: `GET /explain/GBP/USD`

## Roadmap

- [ ] Freemium monetization (free daily explanation quota, pro = unlimited + “alerts with reasons”)
- [ ] Dedicated INR / emerging‑market news coverage
- [ ] Postgres persistence + user accounts
- [ ] Backtesting simple rules described in plain English

## License

Released for educational and portfolio purposes.
