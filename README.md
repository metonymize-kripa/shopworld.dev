# Drop Day — shopworld.dev

A fast, cozy retail sim. You run a brand-new Shopify-style store: customers DM you a *vibe* ("something cozy for my sister, she's always cold"), you read the intent, ship one product, and try to clear a daily profit goal across 6 days without running out of cash or stock.

Built as a self-contained Vite + React app. Email capture is backed by Vercel Blob through one serverless function — no separate backend, no database.

## Run locally

```bash
npm install
npm run dev        # http://localhost:5173
```

## Deploy to Vercel

1. Push this folder to a Git repo.
2. Import it in Vercel — framework auto-detects as **Vite**.
3. Click **Deploy**. The game works immediately.

### Turn on email capture (1 minute)

Email signups no-op gracefully until you connect storage:

1. In your Vercel project: **Storage → Blob → Create / Connect**.
2. Vercel injects `BLOB_READ_WRITE_TOKEN` automatically.
3. **Redeploy.** Signups now persist to `signups.json` in your Blob store.

Read them anytime via the Blob dashboard, or fetch the public JSON URL.

## Design loop

Modeled on *Good Pizza, Great Pizza*'s validated pattern: **ambiguous intent → production action → cost/profit outcome → reinvest → retention.** Drop Day layers the Shopify-specific reality the pizza loop lacks: cash constraints, stock depletion, and restock lead-time choices between days (flash lot = instant + pricey; bulk crate = cheaper, but you commit cash up front).

## Structure

```
api/signup.js     serverless email capture → Vercel Blob
src/App.jsx       game state machine + all screens
src/gameData.js   catalog, customer briefs, scoring rules
src/ui.jsx        HUD bits (coins, rep, patience ring, floaters)
src/styles.css    design tokens
```

## Tuning

All knobs live at the top of `src/App.jsx` (`SECONDS_PER_DAY`, `START_CASH`, `START_STOCK`) and in `src/gameData.js` (`DAY_GOALS`, catalog, briefs).
