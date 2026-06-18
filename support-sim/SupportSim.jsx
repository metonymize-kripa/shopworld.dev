/**
 * Post-Purchase Support Simulator
 * Shows merchants who handles each step of a support workflow —
 * and where the gaps are that Shopworld fills.
 */

import React, { useState } from 'react'

// ─── Data ────────────────────────────────────────────────────────────────────

const STEP_TYPES = {
  native:  { label: 'Shopify handles it',  color: 'var(--mint-deep)',      bg: '#E8F9F4', icon: '✓' },
  app:     { label: 'App Store patch',     color: '#7C5FF5',               bg: '#F0EDFF', icon: '⬡' },
  manual:  { label: 'You handle it',       color: 'var(--tangerine-deep)', bg: '#FFF0E8', icon: '⚙' },
  chaos:   { label: 'Nobody handles it',   color: 'var(--rose)',           bg: '#FFE9EE', icon: '⚠' },
}

const VERDICTS = {
  clean:   {
    label: 'Shopify covers this',
    color: 'var(--mint-deep)',
    bg: '#E8F9F4',
    emoji: '✅',
    hook: null,
  },
  partial: {
    label: 'Gaps you\'re patching manually',
    color: 'var(--tangerine-deep)',
    bg: '#FFF0E8',
    emoji: '⚡',
    hook: 'The manual steps here are where Shopworld saves time per ticket.',
  },
  chaos:   {
    label: 'Nobody owns this — yet',
    color: 'var(--rose)',
    bg: '#FFE9EE',
    emoji: '🔥',
    hook: 'This is the gap Shopworld fills.',
  },
}

const SCENARIOS = [
  {
    id: 'cancel',
    emoji: '🚫',
    title: 'Cancel order',
    trigger: '"I just ordered by mistake — can you cancel?"',
    steps: [
      { label: 'Look up order by email',           type: 'native', detail: 'Orders → Search' },
      { label: 'Confirm order not yet fulfilled',  type: 'native', detail: 'Fulfillment status visible' },
      { label: 'Cancel order + void payment',      type: 'native', detail: 'Orders → Cancel' },
      { label: 'Customer notified automatically',  type: 'native', detail: 'Shopify sends cancellation email' },
    ],
    verdict: 'clean',
    note: 'Shopify handles this end-to-end if the order hasn\'t shipped. Once a label is printed, you\'re calling the carrier.',
  },
  {
    id: 'address',
    emoji: '📍',
    title: 'Change shipping address',
    trigger: '"I moved — update my address before it ships?"',
    steps: [
      { label: 'Find order',                                type: 'native', detail: 'Orders → Search' },
      { label: 'Edit address (unfulfilled only)',           type: 'native', detail: 'Order → Edit → Shipping address' },
      { label: 'Reprint label if already generated',       type: 'manual', detail: 'Void + reprint in Shopify Shipping or carrier portal' },
      { label: 'Contact carrier if package is in transit', type: 'chaos',  detail: 'Phone/chat with UPS/FedEx — success rate ~50%' },
    ],
    verdict: 'partial',
    note: 'Works before fulfillment. After the label prints, someone has to call the carrier — and that someone is you.',
  },
  {
    id: 'swap',
    emoji: '🔄',
    title: 'Swap size or variant',
    trigger: '"I ordered a Medium but I need a Large — can you swap it?"',
    steps: [
      { label: 'Find order',                               type: 'native', detail: 'Orders → Search' },
      { label: 'Check inventory for correct variant',      type: 'native', detail: 'Products → Inventory' },
      { label: 'Cancel original order',                    type: 'native', detail: 'Orders → Cancel (if unfulfilled)' },
      { label: 'Customer manually places new order',       type: 'chaos',  detail: 'No native "swap variant on paid order" — customer must reorder' },
      { label: 'Handle price difference or discount code', type: 'manual', detail: 'Issue discount via email or draft order' },
    ],
    verdict: 'chaos',
    note: 'Shopify has no native variant-swap on a paid order. Cancel + new draft order is the cleanest path — but it\'s a 5-step manual process per ticket.',
  },
  {
    id: 'return',
    emoji: '📦',
    title: 'Return item',
    trigger: '"I want to return this — how do I send it back?"',
    steps: [
      { label: 'Customer requests return',                type: 'manual', detail: 'Via email or contact form — no native self-service portal' },
      { label: 'Generate return shipping label',          type: 'app',    detail: 'Loop Returns, AfterShip, or Shopify basic returns' },
      { label: 'Track return in transit',                 type: 'app',    detail: 'App provides tracking; native Shopify doesn\'t' },
      { label: 'Inspect item on receipt',                 type: 'manual', detail: 'Physical inspection before refunding' },
      { label: 'Issue refund',                            type: 'native', detail: 'Orders → Refund' },
    ],
    verdict: 'partial',
    note: 'Shopify has basic return support but no self-service portal. Apps patch the label and tracking gap — but intake and inspection are still on you.',
  },
  {
    id: 'refund',
    emoji: '💸',
    title: 'Partial refund',
    trigger: '"One item was wrong — can you refund just that one?"',
    steps: [
      { label: 'Open order',                  type: 'native', detail: 'Orders → find order' },
      { label: 'Select line items to refund', type: 'native', detail: 'Refund → choose quantities' },
      { label: 'Set refund amount',           type: 'native', detail: 'Shopify calculates; override if needed' },
      { label: 'Restock inventory',           type: 'native', detail: 'Toggle restock on refund screen' },
      { label: 'Customer notified',           type: 'native', detail: 'Automatic refund confirmation email' },
    ],
    verdict: 'clean',
    note: 'Partial refunds are fully native — one of the few post-purchase flows Shopify does cleanly out of the box.',
  },
  {
    id: 'damaged',
    emoji: '💔',
    title: 'Damaged package',
    trigger: '"My order arrived smashed — I have photos."',
    steps: [
      { label: 'Customer sends photo evidence',             type: 'manual', detail: 'Email or DM — no native damage reporting' },
      { label: 'Log incident in order notes',              type: 'native', detail: 'Orders → Add note' },
      { label: 'Decide: reship or refund',                 type: 'manual', detail: 'Judgment call — policy-dependent' },
      { label: 'Issue refund or create replacement order', type: 'native', detail: 'Refund or duplicate order' },
      { label: 'File carrier claim',                       type: 'manual', detail: 'UPS/FedEx claims portal — 10–20 min per claim' },
    ],
    verdict: 'partial',
    note: 'Customer resolution is fine — refund or reship natively. The carrier claim is manual every time, with no Shopify integration.',
  },
  {
    id: 'wismo',
    emoji: '📡',
    title: 'Late shipment / WISMO',
    trigger: '"I ordered 12 days ago and nothing arrived — where is it?"',
    steps: [
      { label: 'Look up order and fulfillment',         type: 'native', detail: 'Orders → Fulfillments → Tracking' },
      { label: 'Check carrier tracking page',           type: 'manual', detail: 'Copy tracking number → carrier site' },
      { label: 'Contact carrier about delay',           type: 'chaos',  detail: 'Phone/chat — often no resolution' },
      { label: 'Decide: wait, reship, or refund',       type: 'manual', detail: 'Judgment call based on days in transit and carrier SLA' },
      { label: 'Communicate update to customer',        type: 'manual', detail: 'Manual email — no native delay notification' },
    ],
    verdict: 'chaos',
    note: 'Highest-volume ticket type. Least automated. Shopify shows tracking numbers but doesn\'t monitor them — every delay is a manual investigation.',
  },
  {
    id: 'chargeback',
    emoji: '⚖️',
    title: 'Chargeback dispute',
    trigger: 'Card network files dispute: "Item not received."',
    steps: [
      { label: 'Shopify flags dispute in admin',          type: 'native', detail: 'Payments → Disputes' },
      { label: 'Gather order + payment proof',            type: 'native', detail: 'Order timeline, payment confirmation' },
      { label: 'Gather delivery confirmation',            type: 'manual', detail: 'Screenshot carrier delivery scan manually' },
      { label: 'Compile customer communication history',  type: 'chaos',  detail: 'Dig through email/DMs — no unified inbox' },
      { label: 'Write and submit dispute response',       type: 'manual', detail: 'Submit to bank via Shopify Payments — 72hr deadline' },
    ],
    verdict: 'chaos',
    note: 'Shopify surfaces the dispute but gathering evidence is a scavenger hunt. No native evidence packager — every chargeback is a manual scramble against the clock.',
  },
]

// ─── Component ───────────────────────────────────────────────────────────────

export default function SupportSim({ onBack }) {
  const [active, setActive] = useState(null)
  const scenario = SCENARIOS.find(s => s.id === active)

  return (
    <div className="fill">
      {scenario
        ? <Detail scenario={scenario} onBack={() => setActive(null)} />
        : <Inbox scenarios={SCENARIOS} onSelect={setActive} onBack={onBack} />
      }
    </div>
  )
}

// ─── Inbox ───────────────────────────────────────────────────────────────────

function Inbox({ scenarios, onSelect, onBack }) {
  return (
    <div className="fill">
      <div style={{ padding: 'max(20px, env(safe-area-inset-top)) 18px 0' }}>
        <button
          onClick={onBack}
          style={{ fontSize: 13, color: 'var(--ink-soft)', fontFamily: 'var(--display)', fontWeight: 600, marginBottom: 14 }}
        >
          ← Back
        </button>
        <div className="kicker">shopworld.dev</div>
        <h1 className="display" style={{ fontSize: 'clamp(30px, 9vw, 40px)', marginTop: 6, lineHeight: 1.05 }}>
          Support<br />
          <span style={{ color: 'var(--mint-deep)' }}>Simulator.</span>
        </h1>
        <p style={{ marginTop: 10, fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.5 }}>
          Pick a customer request and see who actually handles each step — Shopify, an app, or you.
        </p>

        <div style={{ marginTop: 14, marginBottom: 16 }}>
          <div className="kicker" style={{ marginBottom: 8 }}>Who handles each step</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {Object.entries(STEP_TYPES).map(([key, t]) => (
              <span key={key} style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                fontSize: 11, fontFamily: 'var(--display)', fontWeight: 600,
                padding: '4px 9px', borderRadius: 999,
                color: t.color, background: t.bg, border: `1px solid ${t.color}22`,
              }}>
                {t.icon} {t.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="fill scroll" style={{ padding: '0 18px max(24px, env(safe-area-inset-bottom))' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {scenarios.map((s, i) => {
            const verdict = VERDICTS[s.verdict]
            return (
              <button
                key={s.id}
                className="card focus-ring slide-up"
                onClick={() => onSelect(s.id)}
                style={{
                  padding: '14px 16px',
                  textAlign: 'left',
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  animationDelay: `${i * 0.04}s`,
                }}
              >
                <span style={{ fontSize: 26, flexShrink: 0 }}>{s.emoji}</span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 15, lineHeight: 1.2 }}>
                    {s.title}
                  </div>
                  <div style={{
                    fontSize: 12, color: 'var(--ink-soft)', marginTop: 4,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {s.trigger}
                  </div>
                  <StepBar steps={s.steps} style={{ marginTop: 8 }} />
                </div>

                <div style={{ flexShrink: 0, textAlign: 'center' }}>
                  <div style={{ fontSize: 18 }}>{verdict.emoji}</div>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function StepBar({ steps, style }) {
  return (
    <div style={{ display: 'flex', gap: 3, ...style }}>
      {steps.map((step, i) => {
        const t = STEP_TYPES[step.type]
        return (
          <div
            key={i}
            title={`${step.label} — ${t.label}`}
            style={{
              flex: 1, height: 4, borderRadius: 999,
              background: t.bg, border: `1px solid ${t.color}55`,
            }}
          />
        )
      })}
    </div>
  )
}

// ─── Detail ──────────────────────────────────────────────────────────────────

function Detail({ scenario, onBack }) {
  const verdict = VERDICTS[scenario.verdict]
  const unownedCount = scenario.steps.filter(s => s.type === 'manual' || s.type === 'chaos').length

  return (
    <div className="fill">
      <div style={{ padding: 'max(20px, env(safe-area-inset-top)) 18px 0' }}>
        <button
          onClick={onBack}
          style={{ fontSize: 13, color: 'var(--ink-soft)', fontFamily: 'var(--display)', fontWeight: 600, marginBottom: 14 }}
        >
          ← All scenarios
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 36 }}>{scenario.emoji}</span>
          <div>
            <div className="kicker">Support scenario</div>
            <h2 className="display" style={{ fontSize: 26, marginTop: 3 }}>{scenario.title}</h2>
          </div>
        </div>

        <div className="card" style={{
          marginTop: 14, padding: '12px 14px',
          background: 'var(--putty-deep)', boxShadow: 'none',
          borderColor: 'var(--line)',
        }}>
          <div className="kicker" style={{ marginBottom: 5 }}>Customer message</div>
          <p style={{ fontSize: 14, fontStyle: 'italic', lineHeight: 1.4 }}>
            {scenario.trigger}
          </p>
        </div>
      </div>

      <div className="fill scroll" style={{ padding: '16px 18px 0' }}>
        <div className="kicker" style={{ marginBottom: 10 }}>Who handles each step</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {scenario.steps.map((step, i) => {
            const t = STEP_TYPES[step.type]
            return (
              <div
                key={i}
                className="card slide-up"
                style={{
                  padding: '12px 14px',
                  display: 'flex', alignItems: 'flex-start', gap: 12,
                  animationDelay: `${i * 0.06}s`,
                }}
              >
                <div style={{
                  width: 32, height: 32, borderRadius: 10, flexShrink: 0,
                  background: t.bg, border: `1px solid ${t.color}44`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13, color: t.color,
                }}>
                  {t.icon}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 14, lineHeight: 1.25 }}>
                    {step.label}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginTop: 3 }}>
                    {step.detail}
                  </div>
                </div>

                <span style={{
                  flexShrink: 0, fontSize: 10, fontFamily: 'var(--display)', fontWeight: 700,
                  padding: '3px 7px', borderRadius: 999, marginTop: 1,
                  color: t.color, background: t.bg, border: `1px solid ${t.color}33`,
                  textTransform: 'uppercase', letterSpacing: '.06em', whiteSpace: 'nowrap',
                }}>
                  {t.label}
                </span>
              </div>
            )
          })}
        </div>

        {/* Verdict */}
        <div style={{
          margin: '16px 0 max(24px, env(safe-area-inset-bottom))',
          padding: '16px',
          borderRadius: 'var(--r)',
          background: verdict.bg,
          border: `1px solid ${verdict.color}44`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 20 }}>{verdict.emoji}</span>
            <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 15, color: verdict.color }}>
              {verdict.label}
            </span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--ink-soft)', lineHeight: 1.5 }}>
            {scenario.note}
          </p>
          {verdict.hook && (
            <p style={{
              marginTop: 10, paddingTop: 10,
              borderTop: `1px solid ${verdict.color}33`,
              fontSize: 13, fontFamily: 'var(--display)', fontWeight: 600,
              color: verdict.color,
            }}>
              {unownedCount > 0 && `${unownedCount} step${unownedCount > 1 ? 's' : ''} land on you. `}{verdict.hook}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
