# Deploying the FX Treasury Dashboard

Two free services: **Render** (backend API) and **Vercel** (frontend). ~15 minutes.

## 1. Push the code to GitHub
```bash
git add -A
git commit -m "Add why-it-moved feature + deploy config"
git push origin main
```
> Your `.env` is gitignored — keys stay local. You'll set them in the host dashboards.

## 2. Backend on Render
1. Go to [render.com](https://render.com) → **New → Blueprint** → connect this repo.
2. Render reads `render.yaml` and creates the `fx-treasury-api` web service.
3. When prompted, set the **secret** env vars:
   - `TWELVE_DATA_API_KEY` = your Twelve Data key
   - `GEMINI_API_KEY` = your Gemini key
   - `FRONTEND_ORIGIN` = your Vercel URL (fill in after step 3, then redeploy)
4. Deploy. Note the URL, e.g. `https://fx-treasury-api.onrender.com`.

> Free tier note: the service sleeps after 15 min idle (first request wakes it, ~30s).
> SQLite resets on redeploy — add a Render Postgres and set `DATABASE_URL` for
> persistence (the code already supports it; `psycopg2-binary` is included).

## 3. Frontend on Vercel
1. Go to [vercel.com](https://vercel.com) → **Add New → Project** → import this repo.
2. Set **Root Directory** = `Frontend` (Vercel auto-detects Vite).
3. Add env var `VITE_API_BASE_URL` = your Render backend URL (from step 2).
4. Deploy. You get a URL like `https://fx-treasury-dashboard.vercel.app`.

## 4. Connect them
Back in Render, set `FRONTEND_ORIGIN` to your Vercel URL and redeploy (fixes CORS).

Done — your dashboard is public.
