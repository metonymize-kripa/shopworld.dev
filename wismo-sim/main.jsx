import React from 'react'
import ReactDOM from 'react-dom/client'
import WismoSim from './WismoSim.jsx'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <div className="frame">
      <WismoSim />
    </div>
  </React.StrictMode>,
)
