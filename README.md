# Drop Day — shopworld.dev

Drop Day is a fast, cozy retail simulator about reading customer intent under pressure. You run a brand-new Shopify-style store where customers DM you a *vibe* instead of a SKU, you choose one product to ship, and you try to survive six increasingly demanding sales days without running out of cash or stock.

The project is intentionally small: a self-contained Vite + React game, one Vercel serverless function for email capture, and no separate database service.

## What you do in the game

- Read ambiguous customer briefs like “something cozy for my sister, she’s always cold.”
- Pick a product from a fixed catalog before the customer’s patience timer runs out.
- Earn profit and reputation for good matches, lose cash and reputation on refunds, and watch stock drain with every shipment.
- Clear each day’s profit goal, then decide whether to buy an instant flash lot, a cheaper bulk crate, or skip restocking.
- Survive all 6 days to turn the store into a brand.

## Tech stack

- **Vite 5** for local development and production builds.
- **React 18** for the game UI and state machine.
- **Vercel Functions** for `/api/signup`.
- **Vercel Blob** for optional email signup storage.
- **Plain CSS** for the mobile-first, phone-framed interface.

## Project structure

```text
api/signup.js     Serverless POST endpoint for email capture via Vercel Blob
public/favicon.svg
src/App.jsx       Main game state machine, screens, restock flow, and signup UI
src/gameData.js   Catalog, customer briefs, scoring rules, restock offers, day goals
src/main.jsx      React entry point
src/styles.css    Design tokens, layout, components, animations
src/ui.jsx        Shared HUD pieces: cash, reputation, patience ring, floaters
index.html        Vite HTML shell
vercel.json       Vercel build/output configuration
vite.config.js    Vite React plugin configuration
```

## Local development

### Prerequisites

- Node.js 18 or newer.
- npm.

### Install and run

```bash
npm install
npm run dev
```

Vite serves the app at `http://localhost:5173` by default.

### Build and preview

```bash
npm run build
npm run preview
```

`npm run build` writes the production bundle to `dist/`.

## Email capture

The signup form posts JSON to `/api/signup`:

```json
{ "email": "you@example.com" }
```

The endpoint validates the email, deduplicates by address, and stores entries in a private Blob object named `signups.json` when `BLOB_READ_WRITE_TOKEN` is available.

Without `BLOB_READ_WRITE_TOKEN`, the endpoint returns a successful no-op response so local gameplay and deployments without storage do not crash. The frontend currently shows signup as unavailable when storage is not configured.

### Enable signups on Vercel

1. Import the repo into Vercel. The project is configured as a Vite app.
2. In the Vercel project, go to **Storage → Blob → Create / Connect**.
3. Confirm Vercel adds `BLOB_READ_WRITE_TOKEN` to the project environment.
4. Redeploy.
5. New signups are persisted to `signups.json` in the Blob store.

## Deployment

1. Push this repository to your Git provider.
2. Import it in Vercel.
3. Vercel uses `vercel.json` to run `vite build` and serve the `dist` output directory.
4. Deploy.

The game can run without Blob storage; only persistent email capture requires the Blob integration.

## Gameplay tuning

The main balance knobs are intentionally easy to find:

- `SECONDS_PER_DAY`, `START_CASH`, and `START_STOCK` live near the top of `src/App.jsx`.
- `DAY_GOALS`, `CATALOG`, `RESTOCK_OFFERS`, and customer `BRIEFS` live in `src/gameData.js`.
- Product matching is handled by `resolveOrder()` in `src/gameData.js`:
  - matching wanted tags increases profit/reputation outcomes,
  - avoided tags or severe budget misses trigger refunds,
  - irrelevant but harmless items can still produce partial profit with a reputation penalty.

## Design notes

Drop Day follows a compact loop inspired by cozy service games:

> ambiguous intent → production action → cost/profit outcome → reinvest → retention

The Shopify-style layer adds cash pressure, limited inventory, restock choices, and customer reputation. The UI is mobile-first, but desktop users see the game inside a centered phone-shaped frame.

## Available npm scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Start the Vite development server. |
| `npm run build` | Create a production build in `dist/`. |
| `npm run preview` | Serve the production build locally for review. |

## Notes for future work

- Add a lockfile so installs are fully reproducible.
- Add automated tests for scoring and signup validation.
- Persist more gameplay analytics, such as day reached, final cash, and most-refunded products.
- Consider rate limiting or bot protection before using signup capture for a public launch.
