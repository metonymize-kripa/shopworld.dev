import { STEP_TYPES } from '../../packages/shopworld-scenarios/src/wismo/index.js'

export default function OverviewSection({ scenario, level }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="card" style={{ padding: '14px 16px' }}>
        <div className="kicker" style={{ marginBottom: 8 }}>Workflow Level</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <span className={`level-badge level-${scenario.level.toLowerCase()}`} style={{ fontSize: 12, padding: '4px 10px' }}>
            {level.label}
          </span>
        </div>
        <p style={{ fontSize: 13, color: 'var(--ink-soft)', lineHeight: 1.5 }}>
          {scenario.levelJustification}
        </p>
      </div>

      <div>
        <div className="kicker" style={{ marginBottom: 10 }}>Resolution Steps</div>
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
                  width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                  background: t.bg, border: `1px solid ${t.color}44`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'var(--display)', fontWeight: 700, fontSize: 12, color: t.color,
                }}>
                  {t.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 13, lineHeight: 1.25 }}>
                    {step.label}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--ink-soft)', marginTop: 3, fontFamily: 'monospace' }}>
                    {step.detail}
                  </div>
                </div>
                <span style={{
                  flexShrink: 0, fontSize: 9, fontFamily: 'var(--display)', fontWeight: 700,
                  padding: '2px 6px', borderRadius: 999,
                  color: t.color, background: t.bg, border: `1px solid ${t.color}33`,
                  textTransform: 'uppercase', letterSpacing: '.06em',
                }}>
                  {step.type}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="card" style={{ padding: '14px 16px', background: level.bg, borderColor: `${level.color}44` }}>
        <div style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 14, color: level.color, marginBottom: 8 }}>
          Analysis
        </div>
        <p style={{ fontSize: 13, color: 'var(--ink-soft)', lineHeight: 1.5 }}>
          {scenario.note}
        </p>
      </div>
    </div>
  )
}
