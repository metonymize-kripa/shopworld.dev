import React from 'react'
import ReactDOM from 'react-dom/client'
import SupportSim from './SupportSim.jsx'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <div className="frame">
      <SupportSim onBack={() => {}} />
    </div>
  </React.StrictMode>
)
