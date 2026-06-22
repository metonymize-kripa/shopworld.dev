import { useEffect, useRef } from 'react'

export default function WismoInfoModal({ open, onClose }) {
  const backdropRef = useRef(null)

  useEffect(() => {
    if (open) {
      const handler = (e) => { if (e.key === 'Escape') onClose() }
      document.addEventListener('keydown', handler)
      return () => document.removeEventListener('keydown', handler)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      ref={backdropRef}
      onClick={(e) => { if (e.target === backdropRef.current) onClose() }}
      style={{
        position: 'fixed', inset: 0, zIndex: 999,
        background: 'rgba(27,26,23,.65)',
        backdropFilter: 'blur(6px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 20,
      }}
    >
      <div
        className="card slide-up"
        style={{
          maxWidth: 380, width: '100%',
          padding: '28px 24px 24px',
          position: 'relative',
        }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="focus-ring"
          style={{
            position: 'absolute', top: 14, right: 14,
            width: 28, height: 28, borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'var(--putty)', border: '1px solid var(--line)',
            fontSize: 14, fontWeight: 600, color: 'var(--ink-soft)',
          }}
          aria-label="Close"
        >
          ✕
        </button>

        {/* Header */}
        <div className="kicker" style={{ color: 'var(--mint-deep)' }}>Definition</div>
        <h2
          className="display"
          style={{ fontSize: 26, marginTop: 6, lineHeight: 1.1 }}
        >
          What is WISMO?
        </h2>

        {/* Body */}
        <p style={{ marginTop: 14, fontSize: 14, lineHeight: 1.6, color: 'var(--ink-soft)' }}>
          <strong style={{ color: 'var(--ink)' }}>WISMO — "Where Is My Order?"</strong> — is
          the most common e-commerce support request: customers asking where their package is,
          when it will arrive, or what to do if it is delayed.
        </p>

        {/* Stats */}
        <div style={{
          marginTop: 16, padding: '14px 16px',
          background: 'var(--putty)', borderRadius: 14,
          display: 'flex', gap: 12,
        }}>
          <StatBlock value="25–40%" label="of inbound volume" />
          <div style={{ width: 1, background: 'var(--line)' }} />
          <StatBlock value="50–60%" label="during peak seasons" accent />
        </div>

        <p style={{ marginTop: 14, fontSize: 12, lineHeight: 1.5, color: 'var(--slate)' }}>
          WISMO inquiries account for 25–40% of total inbound support volume for
          e-commerce companies, rising to 50–60% during peak periods such as
          holiday shopping seasons.
        </p>

        {/* Dismiss */}
        <button
          className="btn btn-primary focus-ring"
          onClick={onClose}
          style={{ width: '100%', marginTop: 18, fontSize: 14 }}
        >
          Got it
        </button>
      </div>
    </div>
  )
}

function StatBlock({ value, label, accent }) {
  return (
    <div style={{ flex: 1, textAlign: 'center' }}>
      <div
        className="display"
        style={{
          fontSize: 20,
          color: accent ? 'var(--tangerine)' : 'var(--mint-deep)',
        }}
      >
        {value}
      </div>
      <div style={{ fontSize: 11, color: 'var(--slate)', marginTop: 2 }}>{label}</div>
    </div>
  )
}
