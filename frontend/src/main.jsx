import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ReviewerPanel from "./ReviewerPanel.jsx";

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {window.location.pathname === "/reviewer" ? (
      <ReviewerPanel />
    ) : (
      <App />
    )}
  </StrictMode>,
)
