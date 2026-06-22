function DataField({ label, value, type, highlight }) {
  let color = 'var(--cream)'
  if (type === 'error') color = 'var(--rose)'
  if (type === 'warning') color = 'var(--tangerine)'
  if (highlight) color = 'var(--mint)'
  
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,.08)' }}>
      <span style={{ fontFamily: 'var(--display)', fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.08em', color: 'rgba(255,255,255,.5)', minWidth: 80 }}>
        {label}
      </span>
      <span style={{ fontFamily: 'monospace', fontSize: 12, color }}>
        {value}
      </span>
    </div>
  )
}

export default function DataModelSection({ scenario }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="kicker">Current Data State</div>
      
      {scenario.dataModel.order && (
        <div className="card-dark" style={{ padding: '14px 16px' }}>
          <div style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13, color: 'var(--mint)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16 }}>📋</span>
            Order Object
          </div>
          <div style={{ fontFamily: 'monospace' }}>
            <DataField label="ID" value={scenario.dataModel.order.id} />
            <DataField label="Name" value={scenario.dataModel.order.name} highlight />
            <DataField label="Financial" value={scenario.dataModel.order.financialStatus} />
            <DataField label="Fulfillment" value={scenario.dataModel.order.fulfillmentStatus || 'UNFULFILLED'} />
            {scenario.dataModel.order.canCancel !== undefined && (
              <DataField 
                label="Can Cancel" 
                value={scenario.dataModel.order.canCancel ? 'true' : 'false'}
                type={scenario.dataModel.order.canCancel ? undefined : 'error'}
              />
            )}
          </div>
        </div>
      )}

      {scenario.dataModel.shipment && (
        <div className="card-dark" style={{ padding: '14px 16px' }}>
          <div style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13, color: 'var(--lilac)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16 }}>🚚</span>
            Shipment Object
          </div>
          <div style={{ fontFamily: 'monospace' }}>
            <DataField label="Status" value={scenario.dataModel.shipment.status} />
            <DataField label="Last Scan" value={scenario.dataModel.shipment.lastScan?.slice(0, 10) || 'N/A'} />
            {scenario.dataModel.shipment.daysSinceScan !== undefined && (
              <DataField 
                label="Days Stale" 
                value={`${scenario.dataModel.shipment.daysSinceScan} days`}
                type={scenario.dataModel.shipment.daysSinceScan > 5 ? 'error' : 'warning'}
              />
            )}
            <DataField label="ETA" value={scenario.dataModel.shipment.estimatedDelivery || 'Unknown'} />
            {scenario.dataModel.shipment.exceptionCode && (
              <DataField label="Exception" value={scenario.dataModel.shipment.exceptionCode} type="error" />
            )}
          </div>
        </div>
      )}

      {scenario.dataModel.inventory && (
        <div className="card-dark" style={{ padding: '14px 16px' }}>
          <div style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13, color: 'var(--tangerine)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16 }}>📦</span>
            Inventory State
          </div>
          <div style={{ fontFamily: 'monospace' }}>
            {Object.entries(scenario.dataModel.inventory).map(([sku, inv]) => (
              <div key={sku} style={{ marginBottom: 8 }}>
                <div style={{ color: 'rgba(255,255,255,.5)', marginBottom: 4 }}>SKU: {sku}</div>
                <DataField label="Available" value={inv.available} />
                <DataField label="Committed" value={inv.committed} />
                <DataField label="Reserved" value={inv.reserved || 0} />
              </div>
            ))}
          </div>
        </div>
      )}

      {scenario.stateTransitions && (
        <div>
          <div className="kicker" style={{ marginBottom: 10 }}>State Transitions</div>
          <div className="card" style={{ padding: '14px 16px' }}>
            {scenario.stateTransitions.map((trans, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: i < scenario.stateTransitions.length - 1 ? 12 : 0, fontSize: 12 }}>
                <span style={{ fontFamily: 'monospace', background: 'var(--putty-deep)', padding: '4px 8px', borderRadius: 6, color: 'var(--ink-soft)', fontSize: 10 }}>
                  {trans.from}
                </span>
                <span style={{ color: 'var(--ink-soft)' }}>→</span>
                <span style={{ fontFamily: 'monospace', background: 'rgba(22,199,154,.15)', padding: '4px 8px', borderRadius: 6, color: 'var(--mint-deep)', fontSize: 10, fontWeight: 600 }}>
                  {trans.to}
                </span>
                {trans.api && (
                  <span style={{ fontFamily: 'monospace', marginLeft: 'auto', fontSize: 10, color: 'var(--slate)' }}>
                    via {trans.api}
                  </span>
                )}
                {trans.condition && (
                  <span style={{ fontFamily: 'monospace', marginLeft: 'auto', fontSize: 10, color: 'var(--tangerine)' }}>
                    if {trans.condition}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
