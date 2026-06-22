/**
 * Post-Purchase Support Simulator
 * Shows merchants who handles each step of a support workflow —
 * and where the gaps are that Shopworld fills.
 */

import React, { useState } from 'react'
import { STEP_TYPES, VERDICTS, SCENARIOS } from '../packages/shopworld-scenarios/src/support/index.js'

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
