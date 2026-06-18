import React, { useEffect, useRef, useState } from 'react'

export function Coins({ value }) {
  return (
    <span className="chip" style={{ background: '#fff', borderColor: 'var(--line)' }}>
      <span style={{ fontSize: 14 }}>💵</span>
      <span style={{ fontFamily: 'var(--display)', fontWeight: 700 }}>${value}</span>
    </span>
  )
}

export function RepStars({ rep }) {
  const filled = Math.max(0, Math.min(5, Math.round(rep / 20)))
  return (
    <span className="chip" title={`Reputation ${rep}/100`}>
      <span>{'⭐️'.repeat(filled || 1)}</span>
    </span>
  )
}

// Countdown ring around the active customer
export function PatienceRing({ pct, danger }) {
  const r = 26, c = 2 * Math.PI * r
  return (
    <svg width="64" height="64" viewBox="0 0 64 64" style={{ transform: 'rotate(-90deg)' }}>
      <circle cx="32" cy="32" r={r} fill="none" stroke="var(--putty-deep)" strokeWidth="5" />
      <circle cx="32" cy="32" r={r} fill="none"
        stroke={danger ? 'var(--rose)' : 'var(--mint)'} strokeWidth="5" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
        style={{ transition: 'stroke-dashoffset .25s linear, stroke .3s' }} />
    </svg>
  )
}

// Floating +/- profit numbers
export function Floaters({ items }) {
  return items.map(f => (
    <div key={f.key} className="floater"
      style={{ left: f.x, top: f.y, color: f.delta >= 0 ? 'var(--mint-deep)' : 'var(--rose)' }}>
      {f.delta >= 0 ? `+$${f.delta}` : `-$${Math.abs(f.delta)}`}
    </div>
  ))
}

export function useFloaters() {
  const [items, setItems] = useState([])
  const idRef = useRef(0)
  const push = (delta, x, y) => {
    const key = ++idRef.current
    setItems(s => [...s, { key, delta, x, y }])
    setTimeout(() => setItems(s => s.filter(i => i.key !== key)), 1000)
  }
  return [items, push]
}
