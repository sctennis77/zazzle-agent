import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import App from './App'
import { DonationTierProvider } from './hooks/useDonationTiers'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <DonationTierProvider>
      <App />
    </DonationTierProvider>
  </React.StrictMode>,
)
