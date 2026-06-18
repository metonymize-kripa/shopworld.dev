import React, { useEffect, useMemo, useRef, useState } from 'react'
import { CATALOG, nextCustomer, resolveOrder, RESTOCK_OFFERS, DAY_GOALS } from './gameData.js'
import { Coins, RepStars, PatienceRing, Floaters, useFloaters } from './ui.jsx'

const SECONDS_PER_DAY = 45
const START_CASH = 25
const START_STOCK = 12

export default function App() {
  const [screen, setScreen] = useState('title') // title | play | restock | dayend | over | win
  const [game, setGame] = useState(null)
  const [signedUp, setSignedUp] = useState(false)

  function startGame() {
    setGame({
      day: 1,
      cash: START_CASH,
      rep: 60,
      stock: START_STOCK,
      goal: DAY_GOALS[0],
      dayProfit: 0,
      served: 0,
      log: [],
    })
    setScreen('play')
  }

  return (
    <div className="frame">
      {screen === 'title' && <Title onStart={startGame} signedUp={signedUp} setSignedUp={setSignedUp} />}
      {screen === 'play' && <Play game={game} setGame={setGame} setScreen={setScreen} />}
      {screen === 'restock' && <Restock game={game} setGame={setGame} setScreen={setScreen} />}
      {screen === 'dayend' && <DayEnd game={game} setGame={setGame} setScreen={setScreen} />}
      {screen === 'over' && <GameOver game={game} onRetry={startGame} signedUp={signedUp} setSignedUp={setSignedUp} />}
      {screen === 'win' && <Win game={game} onRetry={startGame} signedUp={signedUp} setSignedUp={setSignedUp} />}
    </div>
  )
}

/* ─────────────────────────── TITLE ─────────────────────────── */
function Title({ onStart, signedUp, setSignedUp }) {
  return (
    <div className="fill" style={{ padding: '0 22px' }}>
      <div className="scroll fill" style={{ paddingTop: 'max(28px, env(safe-area-inset-top))' }}>
        <div className="kicker pop" style={{ animationDelay: '.05s' }}>shopworld.dev presents</div>

        <h1 className="display" style={{ fontSize: 'clamp(54px, 17vw, 80px)', marginTop: 14 }}>
          <span className="pop" style={{ display: 'block', animationDelay: '.1s' }}>Drop</span>
          <span className="pop" style={{ display: 'block', animationDelay: '.18s', color: 'var(--mint-deep)' }}>Day.</span>
        </h1>

        <p className="slide-up" style={{ marginTop: 16, fontSize: 17, lineHeight: 1.45, color: 'var(--ink-soft)', maxWidth: 320, animationDelay: '.25s' }}>
          You just opened a store. Customers slide into your DMs with a <em>vibe</em>, not an order.
          Read them. Ship the right thing. Keep the lights on.
        </p>

        <div className="slide-up" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 20, animationDelay: '.3s' }}>
          <span className="chip">🧠 Read intent</span>
          <span className="chip">📦 Watch stock</span>
          <span className="chip">💵 Don't go broke</span>
        </div>

        {/* preview ticket */}
        <div className="card slide-up" style={{ marginTop: 24, padding: 18, animationDelay: '.36s' }}>
          <div className="kicker">Incoming DM</div>
          <p style={{ marginTop: 8, fontSize: 16, fontWeight: 600 }}>
            "something cozy for my sister, she's always cold" 🧣
          </p>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <div className="chip" style={{ background: 'var(--putty)' }}>🧦 Socks?</div>
            <div className="chip" style={{ background: 'var(--putty)' }}>🔊 Speaker?</div>
            <div className="chip" style={{ background: 'var(--putty)' }}>🪴 Plant?</div>
          </div>
        </div>

        <EmailGate signedUp={signedUp} setSignedUp={setSignedUp} />
        <div style={{ height: 20 }} />
      </div>

      <div style={{ padding: '12px 0 max(20px, env(safe-area-inset-bottom))' }}>
        <button className="btn btn-mint focus-ring" style={{ width: '100%', fontSize: 18 }} onClick={onStart}>
          Open the store →
        </button>
        <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--ink-soft)', marginTop: 10 }}>
          6 days to hit ${DAY_GOALS[DAY_GOALS.length - 1]} total profit.
        </p>
      </div>
    </div>
  )
}

/* ─────────────────────────── PLAY ─────────────────────────── */
function Play({ game, setGame, setScreen }) {
  const [customer, setCustomer] = useState(() => nextCustomer())
  const [timeLeft, setTimeLeft] = useState(SECONDS_PER_DAY)
  const [patience, setPatience] = useState(customer.patience)
  const [feedback, setFeedback] = useState(null) // {outcome, note}
  const [shake, setShake] = useState(false)
  const [floaters, pushFloater] = useFloaters()
  const localRef = useRef({ cash: game.cash, rep: game.rep, stock: game.stock, dayProfit: game.dayProfit, served: game.served })

  // day clock
  useEffect(() => {
    const t = setInterval(() => {
      setTimeLeft(s => {
        if (s <= 1) { clearInterval(t); endDay(); return 0 }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(t)
    // eslint-disable-next-line
  }, [])

  // patience clock per customer
  useEffect(() => {
    setPatience(customer.patience)
    const t = setInterval(() => {
      setPatience(p => {
        if (p <= 1) { clearInterval(t); bounce(); return 0 }
        return p - 1
      })
    }, 1000)
    return () => clearInterval(t)
    // eslint-disable-next-line
  }, [customer.id])

  function commit(next) {
    setGame(g => ({ ...g, ...next }))
  }

  function endDay() {
    const L = localRef.current
    setGame(g => ({ ...g, cash: L.cash, rep: L.rep, stock: L.stock, dayProfit: L.dayProfit, served: L.served }))
    setScreen('dayend')
  }

  function bounce() {
    setFeedback({ outcome: 'left', note: 'Customer got bored and left 👋' })
    localRef.current.rep = Math.max(0, localRef.current.rep - 3)
    commit({ rep: localRef.current.rep })
    setTimeout(nextCust, 700)
  }

  function nextCust() {
    setFeedback(null)
    setCustomer(nextCustomer())
  }

  function pick(product, e) {
    if (feedback) return
    if (localRef.current.stock <= 0) {
      setShake(true); setTimeout(() => setShake(false), 400)
      setFeedback({ outcome: 'refund', note: 'Out of stock! Restock between days.' })
      setTimeout(nextCust, 900)
      return
    }
    const res = resolveOrder(customer, product)
    const L = localRef.current
    L.stock -= 1
    L.cash += res.delta
    L.dayProfit += res.delta
    L.rep = Math.max(0, Math.min(100, L.rep + res.rep))
    L.served += 1
    commit({ cash: L.cash, rep: L.rep, stock: L.stock, dayProfit: L.dayProfit, served: L.served })

    const rect = e?.currentTarget?.getBoundingClientRect?.()
    if (rect) pushFloater(res.delta, rect.left + rect.width / 2 - 20, rect.top - 10)

    setFeedback({ outcome: res.outcome, note: res.note, emoji: product.emoji })
    if (res.outcome === 'refund') { setShake(true); setTimeout(() => setShake(false), 400) }

    if (L.cash < 0) { setTimeout(() => setScreen('over'), 700); return }
    setTimeout(nextCust, 850)
  }

  const dangerTime = timeLeft <= 10
  const dangerPatience = patience <= 5

  return (
    <div className="fill">
      {/* HUD */}
      <div style={{ padding: 'max(16px, env(safe-area-inset-top)) 18px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="kicker">Day {game.day} of 6</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Coins value={game.cash} />
            <RepStars rep={game.rep} />
          </div>
        </div>

        {/* goal bar + timer */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
          <div style={{ flex: 1 }}>
            <div className="bar">
              <span style={{
                width: `${Math.min(100, Math.max(0, (game.dayProfit / game.goal) * 100))}%`,
                background: game.dayProfit >= game.goal ? 'var(--mint)' : 'var(--tangerine)',
              }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5, fontSize: 11, color: 'var(--ink-soft)', fontFamily: 'var(--display)', fontWeight: 600 }}>
              <span>${game.dayProfit} profit</span><span>goal ${game.goal}</span>
            </div>
          </div>
          <div style={{
            fontFamily: 'var(--display)', fontWeight: 700, fontSize: 22, width: 44, textAlign: 'right',
            color: dangerTime ? 'var(--rose)' : 'var(--ink)',
          }}>{timeLeft}s</div>
        </div>
      </div>

      {/* Customer card */}
      <div className={shake ? 'shake' : undefined} style={{ padding: '0 18px 12px', position: 'relative' }}>
        <Floaters items={floaters} />
        <div className="card" style={{ padding: 18, display: 'flex', gap: 14, alignItems: 'center', animation: 'spinIn .3s ease both' }} key={customer.id}>
          <div style={{ position: 'relative', display: 'grid', placeItems: 'center' }}>
            <PatienceRing pct={patience / customer.patience} danger={dangerPatience} />
            <div style={{ position: 'absolute', fontSize: 30 }}>{customer.avatar}</div>
          </div>
          <div style={{ flex: 1 }}>
            <div className="kicker">New order · ≤ ${customer.budget}</div>
            <p style={{ fontSize: 16, fontWeight: 600, marginTop: 6, lineHeight: 1.3 }}>"{customer.msg}"</p>
          </div>
        </div>

        {/* feedback toast */}
        <div style={{ height: 40, display: 'grid', placeItems: 'center' }}>
          {feedback && (
            <div className="pop" style={{
              fontFamily: 'var(--display)', fontWeight: 700, fontSize: 15,
              color: feedback.outcome === 'love' ? 'var(--mint-deep)'
                : feedback.outcome === 'refund' ? 'var(--rose)'
                : feedback.outcome === 'left' ? 'var(--ink-soft)' : 'var(--ink)',
            }}>
              {feedback.emoji ? feedback.emoji + '  ' : ''}{feedback.note}
            </div>
          )}
        </div>
      </div>

      {/* Catalog grid — fills remaining space and scrolls */}
      <div className="fill scroll" style={{ borderTop: '1px solid var(--line)', padding: '12px 18px max(18px, env(safe-area-inset-bottom))' }}>
        {/* Stock indicator */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div className="kicker">Tap a product to ship</div>
          <span className="chip" style={{ background: game.stock <= 3 ? '#FFE9E2' : 'var(--cream)', borderColor: game.stock <= 3 ? 'var(--tangerine)' : 'var(--line)' }}>
            📦 {game.stock} in stock
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {CATALOG.map(p => (
            <button key={p.id} className="card focus-ring" onClick={(e) => pick(p, e)}
              style={{ padding: 14, textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 30 }}>{p.emoji}</span>
              <span style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 14, lineHeight: 1.1 }}>{p.name}</span>
              <span style={{ fontSize: 12, color: 'var(--ink-soft)' }}>cost ${p.cost} · sell ${p.price}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────── DAY END ─────────────────────────── */
function DayEnd({ game, setGame, setScreen }) {
  const hit = game.dayProfit >= game.goal
  const totalProfit = useMemo(() => game.cash - START_CASH, [game.cash])

  function go() {
    if (!hit) { setScreen('over'); return }
    setScreen('restock')
  }

  return (
    <div className="fill" style={{ padding: '0 22px', justifyContent: 'center' }}>
      <div className="slide-up" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 56 }}>{hit ? '🎉' : '😬'}</div>
        <div className="kicker" style={{ marginTop: 8 }}>Day {game.day} closed</div>
        <h2 className="display" style={{ fontSize: 40, marginTop: 6 }}>
          {hit ? 'Goal cleared' : 'Came up short'}
        </h2>
      </div>

      <div className="card slide-up" style={{ marginTop: 24, padding: 20, animationDelay: '.08s' }}>
        <Row label="Profit today" value={`$${game.dayProfit}`} accent={hit ? 'var(--mint-deep)' : 'var(--rose)'} />
        <Row label="Day goal" value={`$${game.goal}`} />
        <Row label="Orders served" value={game.served} />
        <hr style={{ border: 0, borderTop: '1px solid var(--line)', margin: '12px 0' }} />
        <Row label="Cash on hand" value={`$${game.cash}`} big />
        <Row label="Reputation" value={`${game.rep}/100`} />
      </div>

      <button className="btn btn-mint focus-ring slide-up" style={{ width: '100%', marginTop: 22, fontSize: 17, animationDelay: '.14s' }} onClick={go}>
        {hit ? 'Go to restock →' : 'See results'}
      </button>
    </div>
  )
}

/* ─────────────────────────── RESTOCK ─────────────────────────── */
function Restock({ game, setGame, setScreen }) {
  function choose(offer) {
    if (offer.cost > game.cash && offer.cost > 0) return
    const nextDay = game.day + 1
    const isWin = nextDay > 6
    setGame(g => ({
      ...g,
      day: nextDay,
      cash: g.cash - offer.cost,
      stock: g.stock + offer.restock,
      goal: DAY_GOALS[Math.min(nextDay - 1, DAY_GOALS.length - 1)],
      dayProfit: 0,
      served: 0,
    }))
    setScreen(isWin ? 'win' : 'play')
  }

  return (
    <div className="fill" style={{ padding: '0 22px', justifyContent: 'center' }}>
      <div className="slide-up">
        <div className="kicker">Supplier · between days</div>
        <h2 className="display" style={{ fontSize: 34, marginTop: 6 }}>Restock the shelves</h2>
        <p style={{ color: 'var(--ink-soft)', marginTop: 8, fontSize: 15 }}>
          You have <strong>{game.stock}</strong> units left and <strong>${game.cash}</strong> cash. Buy low, sell high — but don't run dry.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 22 }}>
        {RESTOCK_OFFERS.map((o, i) => {
          const broke = o.cost > game.cash && o.cost > 0
          return (
            <button key={o.id} disabled={broke}
              className="card focus-ring slide-up"
              style={{ padding: 18, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 14, opacity: broke ? .45 : 1, animationDelay: `${i * .06}s` }}
              onClick={() => choose(o)}>
              <span style={{ fontSize: 30 }}>{o.emoji}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 16 }}>{o.label}</div>
                <div style={{ fontSize: 13, color: 'var(--ink-soft)' }}>
                  {o.cost > 0 ? `−$${o.cost} · +${o.restock} units` : 'Free'} · {o.note}
                </div>
              </div>
              <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 22 }}>›</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

/* ─────────────────────────── END SCREENS ─────────────────────────── */
function GameOver({ game, onRetry, signedUp, setSignedUp }) {
  const broke = game.cash < 0
  return (
    <div className="fill" style={{ padding: '0 22px', justifyContent: 'center', textAlign: 'center' }}>
      <div className="slide-up">
        <div style={{ fontSize: 60 }}>{broke ? '💸' : '📉'}</div>
        <h2 className="display" style={{ fontSize: 38, marginTop: 8 }}>Store closed</h2>
        <p style={{ color: 'var(--ink-soft)', marginTop: 8, fontSize: 15 }}>
          {broke ? 'You ran out of cash mid-day.' : `You needed $${game.goal} on day ${game.day} and landed $${game.dayProfit}.`}
        </p>
        <div className="chip" style={{ marginTop: 16 }}>Reached Day {game.day} · {game.rep}/100 rep</div>
      </div>
      <EmailGate signedUp={signedUp} setSignedUp={setSignedUp} compact />
      <button className="btn btn-mint focus-ring" style={{ width: '100%', marginTop: 18, fontSize: 17 }} onClick={onRetry}>
        Try again →
      </button>
    </div>
  )
}

function Win({ game, onRetry, signedUp, setSignedUp }) {
  return (
    <div className="fill" style={{ padding: '0 22px', justifyContent: 'center', textAlign: 'center' }}>
      <div className="slide-up">
        <div style={{ fontSize: 64 }}>🏆</div>
        <div className="kicker" style={{ marginTop: 8 }}>6 days survived</div>
        <h2 className="display" style={{ fontSize: 40, marginTop: 6 }}>You built a brand.</h2>
        <p style={{ color: 'var(--ink-soft)', marginTop: 10, fontSize: 16 }}>
          Final cash <strong style={{ color: 'var(--mint-deep)' }}>${game.cash}</strong> · reputation {game.rep}/100.
          Real Shopify owners do this every day — now imagine doing it with refunds, ad spend, and shipping delays.
        </p>
      </div>
      <EmailGate signedUp={signedUp} setSignedUp={setSignedUp} compact headline="Get the full sim early" />
      <button className="btn btn-ghost focus-ring" style={{ width: '100%', marginTop: 10 }} onClick={onRetry}>
        Play again
      </button>
    </div>
  )
}

/* ─────────────────────────── shared bits ─────────────────────────── */
function Row({ label, value, accent, big }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '4px 0' }}>
      <span style={{ color: 'var(--ink-soft)', fontSize: big ? 15 : 14 }}>{label}</span>
      <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: big ? 22 : 16, color: accent || 'var(--ink)' }}>{value}</span>
    </div>
  )
}

function EmailGate({ signedUp, setSignedUp, compact, headline }) {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [msg, setMsg] = useState('')

  if (signedUp || status === 'done') {
    return (
      <div className="card" style={{ padding: 14, marginTop: compact ? 18 : 22, textAlign: 'center' }}>
        <span style={{ fontFamily: 'var(--display)', fontWeight: 600 }}>✅ You're on the list.</span>
      </div>
    )
  }

  async function submit() {
    if (status === 'loading') return
    setStatus('loading'); setMsg('')
    try {
      const r = await fetch('/api/signup', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await r.json()
      if (!r.ok || !data.ok) { setStatus('error'); setMsg(data.error || 'Something went wrong'); return }
      if (!data.stored) { setStatus('error'); setMsg('Sign-up unavailable right now — try again later'); return }
      setStatus('done'); setSignedUp(true)
    } catch {
      setStatus('error'); setMsg('Network error — try again')
    }
  }

  return (
    <div className="card" style={{ padding: 16, marginTop: compact ? 18 : 22 }}>
      <div className="kicker">{headline || 'Get new drops + the full game'}</div>
      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <input
          className="focus-ring"
          type="email" inputMode="email" autoComplete="email" placeholder="you@store.com"
          value={email} onChange={e => setEmail(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          style={{
            flex: 1, padding: '13px 14px', borderRadius: 14, fontSize: 16,
            border: '1px solid var(--line)', background: '#fff', color: 'var(--ink)',
          }}
        />
        <button className="btn btn-primary focus-ring" style={{ padding: '0 18px' }} onClick={submit} disabled={status === 'loading'}>
          {status === 'loading' ? '…' : 'Join'}
        </button>
      </div>
      {status === 'error' && <p style={{ color: 'var(--rose)', fontSize: 13, marginTop: 8 }}>{msg}</p>}
    </div>
  )
}
