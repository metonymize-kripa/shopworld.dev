// ── ShopWorld Sprint simulator data ──────────────────────────────────────────
// The demo is a compact agentic-commerce loop: infer customer intent,
// choose a safe fulfillment action, and preserve cash, reputation, and stock.
// Correct judgment → margin + trust. Unsafe actions → refunds and trust loss.

export const CATALOG = [
  { id: 'mug',     name: 'Speckled Mug',        emoji: '☕️', cost: 4,  price: 16, tags: ['cozy','home','gift','calm'] },
  { id: 'plant',   name: 'Mini Monstera',       emoji: '🪴', cost: 6,  price: 22, tags: ['plant','green','calm','gift'] },
  { id: 'candle',  name: 'Smoked Fig Candle',   emoji: '🕯️', cost: 5,  price: 24, tags: ['cozy','calm','gift','scent'] },
  { id: 'socks',   name: 'Cloud Crew Socks',    emoji: '🧦', cost: 3,  price: 14, tags: ['cozy','soft','cheap','gift'] },
  { id: 'tote',    name: 'Canvas Day Tote',     emoji: '👜', cost: 7,  price: 28, tags: ['carry','daily','minimal','green'] },
  { id: 'tee',     name: 'Heavyweight Tee',     emoji: '👕', cost: 8,  price: 32, tags: ['daily','minimal','soft','gift'] },
  { id: 'beans',   name: 'Single-Origin Beans', emoji: '🫘', cost: 9,  price: 26, tags: ['coffee','scent','daily','gift'] },
  { id: 'journal', name: 'Linen Journal',       emoji: '📓', cost: 5,  price: 20, tags: ['minimal','calm','gift','daily'] },
  { id: 'lamp',    name: 'Pebble Desk Lamp',    emoji: '💡', cost: 14, price: 48, tags: ['home','minimal','premium','glow'] },
  { id: 'speaker', name: 'Brick Speaker',       emoji: '🔊', cost: 18, price: 64, tags: ['tech','premium','gift','loud'] },
]

// Customer archetypes: each gives a fuzzy brief + the tag(s) that satisfy it.
// `want` = tags that delight, `avoid` = tags that trigger a refund.
const BRIEFS = [
  { msg: "something cozy for my sister, she's always cold", avatar: '🧣', want: ['cozy','soft'], avoid: ['tech','loud'], budget: 30 },
  { msg: "housewarming gift but I don't really know them", avatar: '🎁', want: ['gift','calm','home'], avoid: ['loud'], budget: 35 },
  { msg: "I keep killing every plant. give me an easy win", avatar: '🌱', want: ['plant','green'], avoid: ['tech'], budget: 30 },
  { msg: "need something that smells incredible", avatar: '👃', want: ['scent'], avoid: ['tech','carry'], budget: 30 },
  { msg: "desk is bland. make it look intentional", avatar: '🖥️', want: ['minimal','home','glow'], avoid: ['cozy'], budget: 55 },
  { msg: "gift for my coworker, keep it cheap but cute", avatar: '💸', want: ['cheap','gift'], avoid: ['premium'], budget: 18 },
  { msg: "treat myself. money's not the issue today", avatar: '✨', want: ['premium'], avoid: ['cheap'], budget: 80 },
  { msg: "morning routine upgrade pls", avatar: '🌅', want: ['coffee','scent','calm'], avoid: ['loud'], budget: 30 },
  { msg: "something to carry my whole life around", avatar: '🚶', want: ['carry','daily'], avoid: ['scent','tech'], budget: 35 },
  { msg: "loud party energy, you know the vibe", avatar: '🎉', want: ['loud','tech'], avoid: ['calm'], budget: 75 },
  { msg: "want to journal more in the new year", avatar: '📝', want: ['minimal','calm'], avoid: ['loud','tech'], budget: 25 },
  { msg: "just need a solid everyday basic", avatar: '🧢', want: ['daily','minimal'], avoid: ['premium','scent'], budget: 35 },
]

let seq = 0
export function nextCustomer(rng = Math.random) {
  const b = BRIEFS[Math.floor(rng() * BRIEFS.length)]
  // patience: how many seconds before they bounce (tunable by day)
  return { ...b, id: ++seq, patience: 16 + Math.floor(rng() * 6) }
}

// Score a chosen product against the brief.
// Returns { outcome: 'love'|'ok'|'refund', delta, rep, note }
export function resolveOrder(brief, product) {
  const overBudget = product.price > brief.budget + 6
  const hitsAvoid = product.tags.some(t => brief.avoid.includes(t))
  const wantHits = product.tags.filter(t => brief.want.includes(t)).length

  if (hitsAvoid || (overBudget && wantHits === 0)) {
    return { outcome: 'refund', delta: -product.cost, rep: -8,
      note: hitsAvoid ? "Not what I asked for 😤" : "Way over budget." }
  }
  if (wantHits >= 2 && !overBudget) {
    return { outcome: 'love', delta: product.price - product.cost, rep: +6, note: "Obsessed. 5 stars ⭐️" }
  }
  if (wantHits >= 1) {
    return { outcome: 'ok', delta: product.price - product.cost, rep: +2,
      note: overBudget ? "Pricey, but I like it." : "Yeah, this works." }
  }
  // shipped something irrelevant but harmless → meh sale, low rep
  return { outcome: 'ok', delta: Math.round((product.price - product.cost) * 0.5), rep: -2, note: "Eh. It's fine I guess." }
}

// Daily wholesale restock event — Shopify reality: lead times + cash.
export const RESTOCK_OFFERS = [
  { id: 'flash',  label: 'Flash wholesale lot', emoji: '⚡️', cost: 60, restock: 10, note: 'Arrives now. Pricey.' },
  { id: 'bulk',   label: 'Bulk crate (next day)', emoji: '📦', cost: 90, restock: 22, note: 'Cheaper per unit. 1-day lead.' },
  { id: 'skip',   label: 'Skip restock today', emoji: '🚫', cost: 0,  restock: 0,  note: 'Risk running dry.' },
]

export const DAY_GOALS = [40, 70, 110, 160, 220, 300]
