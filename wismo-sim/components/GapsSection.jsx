export default function GapsSection({ scenario }) {
  const { gapAnalysis } = scenario
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="kicker">Gap Analysis</div>
      
      {gapAnalysis.filled.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--mint)' }}></span>
            <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13, color: 'var(--mint-deep)' }}>
              Filled by Shopify
            </span>
            <span style={{ fontSize: 11, color: 'var(--ink-soft)', marginLeft: 'auto' }}>
              {gapAnalysis.filled.length} items
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {gapAnalysis.filled.map((item, i) => (
              <div key={i} className="card" style={{ padding: '10px 14px', background: 'rgba(22,199,154,.08)', borderColor: 'rgba(22,199,154,.25)' }}>
                <span style={{ fontSize: 12 }}>✓ {item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {gapAnalysis.partial.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--tangerine)' }}></span>
            <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13, color: 'var(--tangerine-deep)' }}>
              Partial / Carrier-Dependent
            </span>
            <span style={{ fontSize: 11, color: 'var(--ink-soft)', marginLeft: 'auto' }}>
              {gapAnalysis.partial.length} items
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {gapAnalysis.partial.map((item, i) => (
              <div key={i} className="card" style={{ padding: '10px 14px', background: 'rgba(255,122,61,.08)', borderColor: 'rgba(255,122,61,.25)' }}>
                <span style={{ fontSize: 12 }}>~ {item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {gapAnalysis.missing.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--rose)' }}></span>
            <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13, color: 'var(--rose)' }}>
              Missing / Manual Gap
            </span>
            <span style={{ fontSize: 11, color: 'var(--ink-soft)', marginLeft: 'auto' }}>
              {gapAnalysis.missing.length} items
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {gapAnalysis.missing.map((item, i) => (
              <div key={i} className="card" style={{ padding: '10px 14px', background: 'rgba(255,92,122,.08)', borderColor: 'rgba(255,92,122,.25)' }}>
                <span style={{ fontSize: 12 }}>✗ {item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card-dark" style={{ padding: '14px 16px', marginTop: 8 }}>
        <div className="kicker" style={{ marginBottom: 8, color: 'rgba(255,255,255,.6)' }}>Shopworld Solution</div>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,.8)', lineHeight: 1.5 }}>
          {gapAnalysis.missing.length === 0 
            ? "This is a clean L0 workflow — Shopify handles it natively. Shopworld passes through without adding overhead."
            : `This workflow has ${gapAnalysis.missing.length} manual gaps that Shopworld fills with: (1) automated state monitoring, (2) external API orchestration, (3) decision logic based on policy + data, and (4) unified customer communication.`}
        </p>
      </div>
    </div>
  )
}
