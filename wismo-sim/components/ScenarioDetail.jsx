import { useState } from 'react'
import { WORKFLOW_LEVELS, SCENARIOS } from '../data.js'
import OverviewSection from './OverviewSection.jsx'
import DataModelSection from './DataModelSection.jsx'
import ApiSection from './ApiSection.jsx'
import GapsSection from './GapsSection.jsx'

export default function ScenarioDetail({ scenarioId, onBack }) {
  const [activeSection, setActiveSection] = useState('overview')
  const scenario = SCENARIOS.find(s => s.id === scenarioId)
  const level = WORKFLOW_LEVELS[scenario.level]

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
            <h2 className="display" style={{ fontSize: 24, marginTop: 3 }}>{scenario.title}</h2>
          </div>
        </div>

        <div className="card" style={{ marginTop: 14, padding: '12px 14px', background: 'var(--putty-deep)', boxShadow: 'none', borderColor: 'var(--line)' }}>
          <div className="kicker" style={{ marginBottom: 5 }}>Customer message</div>
          <p style={{ fontSize: 14, fontStyle: 'italic', lineHeight: 1.4 }}>
            {scenario.trigger}
          </p>
        </div>

        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {['overview', 'data', 'api', 'gaps'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveSection(tab)}
              style={{
                padding: '8px 14px',
                borderRadius: 12,
                fontFamily: 'var(--display)',
                fontSize: 12,
                fontWeight: 600,
                background: activeSection === tab ? 'var(--ink)' : 'var(--cream)',
                color: activeSection === tab ? 'var(--cream)' : 'var(--ink)',
                border: `1px solid ${activeSection === tab ? 'var(--ink)' : 'var(--line)'}`,
              }}
            >
              {tab === 'overview' && 'Overview'}
              {tab === 'data' && 'Data Model'}
              {tab === 'api' && 'API Calls'}
              {tab === 'gaps' && 'Gap Analysis'}
            </button>
          ))}
        </div>
      </div>

      <div className="fill scroll" style={{ padding: '16px 18px max(24px, env(safe-area-inset-bottom))' }}>
        {activeSection === 'overview' && <OverviewSection scenario={scenario} level={level} />}
        {activeSection === 'data' && <DataModelSection scenario={scenario} />}
        {activeSection === 'api' && <ApiSection scenario={scenario} />}
        {activeSection === 'gaps' && <GapsSection scenario={scenario} />}
      </div>
    </div>
  )
}
