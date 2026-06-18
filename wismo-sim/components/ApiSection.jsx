function Metric({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 16, color: 'var(--ink)' }}>
        {value}
      </div>
    </div>
  )
}

export default function ApiSection({ scenario }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="kicker">API Call Sequence</div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {scenario.apiCalls.map((call, i) => (
          <div 
            key={i} 
            style={{
              fontFamily: 'monospace',
              fontSize: 11,
              padding: '10px 12px',
              background: call.type === 'mutation' ? 'rgba(22,199,154,.08)' : 
                         call.type === 'query' ? 'rgba(185,167,255,.08)' : 'rgba(255,92,122,.08)',
              borderRadius: 10,
              borderLeft: `3px solid ${call.type === 'mutation' ? 'var(--mint)' : call.type === 'query' ? 'var(--lilac)' : 'var(--rose)'}`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ 
                fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
                padding: '2px 6px', borderRadius: 4,
                background: call.type === 'mutation' ? 'rgba(22,199,154,.2)' : 
                           call.type === 'query' ? 'rgba(185,167,255,.2)' : 'rgba(255,92,122,.2)',
                color: call.type === 'mutation' ? 'var(--mint-deep)' : 
                       call.type === 'query' ? 'var(--lilac-deep)' : 'var(--rose)',
              }}>
                {call.type}
              </span>
              <span style={{ fontWeight: 600 }}>{call.name}</span>
            </div>
            {call.fields && (
              <div style={{ padding: '6px 8px', background: 'rgba(27,26,23,.04)', borderRadius: 6, fontSize: 10, color: 'var(--slate)' }}>
                {'{ ' + call.fields.join(', ') + ' }'}
              </div>
            )}
            {call.input && (
              <div style={{ padding: '6px 8px', background: 'rgba(22,199,154,.06)', borderRadius: 6, fontSize: 10, color: 'var(--mint-deep)', marginTop: 6 }}>
                input: {call.input}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: '14px 16px' }}>
        <div className="kicker" style={{ marginBottom: 10 }}>Metrics</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Metric label="Resolution Time" value={scenario.metrics.resolutionTime} />
          <Metric label="API Calls" value={scenario.metrics.apiCalls} />
          <Metric label="Manual Steps" value={scenario.metrics.manualSteps} />
          <Metric label="Error Rate" value={scenario.metrics.errorRate} />
        </div>
      </div>

      <div className="card-dark" style={{ padding: '14px 16px' }}>
        <div className="kicker" style={{ marginBottom: 8, color: 'rgba(255,255,255,.6)' }}>Technical Context</div>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,.8)', lineHeight: 1.5 }}>
          Each scenario demonstrates how many external systems must coordinate to resolve a single 
          customer request. L0 workflows stay within Shopify's GraphQL surface. L2+ workflows 
          require orchestrating carrier APIs, 3PL systems, and manual human judgment — 
          precisely where Shopworld provides value.
        </p>
      </div>
    </div>
  )
}
