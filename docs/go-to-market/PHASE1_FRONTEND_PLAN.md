# Phase 1 — Stakeholder Front-End Plan

_Next-level milli.run/ShopWorld web presence. Static, Vercel-deployable, no new backend._
_Status: proposal for review before build. Last updated: 2026-06-22._

## Problem

The current site (milli.run) is an early-launch explainer plus a casual "Agent Sprint" game and two scenario explorers. It conveys vibe, not rigor. For senior leaders at Salsify, Mars, and Family Mart it under-sells what's actually been built: a tested simulator, two agents, and a 270-episode comparative result. The job of Phase 1 is to make the existing evidence legible and credible to a non-technical executive in five minutes, without standing up a backend.

## Constraint that shapes the design

Everything the stakeholder demo needs already exists as static artifacts: `experiments/reports/comparative_report.md` and the 711 KB `results.json` (270 episode records, traces included). **We do not need a live backend to show the result — we need to ship the data that's already computed.** That keeps Phase 1 on Vercel, cheap, and reviewable. Live execution is Phase 2.

## Approach

Build the site as the canonical narrative spine from `STAKEHOLDER_NARRATIVE.md`, with the existing interactive pieces re-cast as supporting evidence rather than the main event. One build pipeline, pre-computed data baked in at build time.

### Information architecture

A single-scroll executive narrative with three optional deep-dives.

1. **Hero / thesis.** "Prove an agent is safe before it touches your store." One line, one CTA. Replaces the current game-first landing.
2. **The problem, in one interaction.** A tight, embedded version of the scenario explorer (WISMO or escalation) — the visitor makes 2–3 granular decisions an agent faces and feels the trap. This is the existing `support-sim`/`wismo-sim` repurposed and shortened. Keep it under a minute.
3. **The result.** The comparative table rendered from `results.json` — the 100% / 83% / 60% headline, collateral = 0, NLU 94%. Interactive: filter by workflow family, toggle agents. This is the slide that wins the room, made explorable.
4. **The proof of rigor.** A trace viewer: pick one episode, see milli.run's audited decision (cause + rollback plan) beside the LLM agent's `policy_drift` failure on the same scenario. Drawn directly from `results.json` traces.
5. **Deep-dive: how the benchmark works.** Architecture diagram (ShopWorld / Merchant API Surface / agents / neutral runner / evaluator), the non-negotiable separation rule, the authority-level ladder. For the technical evaluator in the room.
6. **What's real vs. roadmap.** Explicit. Mirrors the narrative's honesty section.
7. **Audience-aware CTA.** "Talk to us about evaluating your agents / your store."

### Three audience entry points

Add `?lens=salsify|mars|familymart` (or three pretty paths) that swap only the hero example and the section-2 scenario, per the narrative's three accents. Same spine, accented open. Lets the user send a tailored link before each meeting and present from it live.

## Technical design

- **Stack:** keep Vite + React (already in `src/`). No framework change. Single app, route-based sections; the two existing sims become components, not separate deploys.
- **Data:** a build step exports `experiments/reports/results.json` → a trimmed `public/data/benchmark.json` (aggregates + a curated set of ~10 representative traces, not all 270 raw — keep payload small and the narrative sharp). Add `scripts/export-benchmark.mjs` run via `make` / prebuild.
- **Charts:** lightweight (Recharts or hand-rolled SVG) for the comparative bars and the failure-taxonomy breakdown. No heavy deps.
- **Trace viewer:** pure client-side render of pre-exported trace JSON. Step list, tool calls, guard decisions, audit-log entries, final score.
- **Deployment:** unchanged — Vercel static build. The existing `api/signup.js` serverless email capture stays.
- **Consolidation:** fold `support-sim/` and `wismo-sim/` into the root app as embeddable components sourced from `packages/shopworld-scenarios/` (the fixtures are already UI-free and shared). Retire the standalone deploys or keep them as legacy redirects. This removes the "three separate demos" smell the README already flags.

## Build sequence

1. Export pipeline: `results.json` → `public/data/benchmark.json` (aggregates + curated traces). Verify numbers against the source report.
2. New landing + narrative spine (sections 1, 6, 7). Ship the thesis even before interactives are polished.
3. Comparative-result section (3) wired to exported data.
4. Trace viewer (4) — the rigor proof.
5. Re-embed shortened scenario explorer (2) from shared fixtures.
6. Architecture deep-dive (5) + lens routing.
7. Polish, mobile, load test, link-share preview cards.

## Explicitly out of scope for Phase 1

Live agent execution, importing a visitor's real store data, user-submitted scenarios, leaderboard with external submissions, auth, persistence beyond email capture. All of that is Phase 2 and requires the GCP backend — see `PHASE2_BACKEND.md`. Phase 1 ships the evidence we already have, beautifully and credibly, on the infrastructure we already run.

## Definition of done

- An executive with no technical background reaches the comparative table and the trace contrast within two scrolls.
- Every number on the page traces to `results.json` / the test suite, verified by the export script.
- The three lens links render correctly for each meeting.
- Deploys on the current Vercel project with no new services.

---

**TL;DR.** The winning evidence is already computed and sitting in `results.json`. Phase 1 is a presentation problem, not an engineering one: ship a single narrative-driven site that renders the comparative result and a side-by-side audited trace, with three audience-accented entry points, on the Vercel stack we already have. No backend required.
