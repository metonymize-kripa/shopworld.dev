import { WORKFLOW_LEVELS, STEP_TYPES, SCENARIOS } from '../data.js'

function StepBar({ steps }) {
  return (
    <div style={{ display: 'flex', gap: 2, flex: 1 }}>
      {steps.slice(0, 6).map((step, i) => {
        const t = STEP_TYPES[step.type]
        return (
          <div
            key={i}
            title={step.label}
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

export default function ScenarioInbox({ onSelect }) {
  return (
    <div className="fill">
      <div style={{ padding: 'max(20px, env(safe-area-inset-top)) 18px 0' }}>
        <div className="kicker">shopworld.dev</div>
        <h1 className="display" style={{ fontSize: 'clamp(30px, 9vw, 40px)', marginTop: 6, lineHeight: 1.05 }}>
          WISMO<br />
          <span style={{ color: 'var(--mint-deep)' }}>Simulator.</span>
        </h1>
        <p style={{ marginTop: 10, fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.5 }}>
          Technical deep-dive into post-purchase support. See the API calls, state transitions, and gaps.
        </p>

        <div style={{ marginTop: 14, marginBottom: 16 }}>
          <div className="kicker" style={{ marginBottom: 8 }}>Workflow Cleanliness Levels</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.entries(WORKFLOW_LEVELS).map(([key, level]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, fontFamily: 'var(--display)', fontWeight: 600 }}>
                <span className={`level-badge level-${key.toLowerCase()}`}>{key}</span>
                <span style={{ color: 'var(--ink-soft)' }}>{level.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="fill scroll" style={{ padding: '0 18px max(24px, env(safe-area-inset-bottom))' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {SCENARIOS.map((s, i) => {
            const level = WORKFLOW_LEVELS[s.level]
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
                  <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {s.trigger}
                  </div>
                  <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className={`level-badge level-${s.level.toLowerCase()}`}>{s.level}</span>
                    <StepBar steps={s.steps} />
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
