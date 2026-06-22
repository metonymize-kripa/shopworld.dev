/**
 * WISMO Simulator — Post-Purchase Support World MVP
 * Technically explanatory demo showing how our runtime handles
 * "Where Is My Order" scenarios with full state transparency
 */

import { useState } from 'react'
import ScenarioInbox from './components/ScenarioInbox.jsx'
import ScenarioDetail from './components/ScenarioDetail.jsx'

export default function WismoSim() {
  const [activeScenario, setActiveScenario] = useState(null)

  return (
    <div className="fill">
      {activeScenario ? (
        <ScenarioDetail 
          scenarioId={activeScenario} 
          onBack={() => setActiveScenario(null)} 
        />
      ) : (
        <ScenarioInbox onSelect={setActiveScenario} />
      )}
    </div>
  )
}
