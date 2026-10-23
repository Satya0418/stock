/**
 * ==============================================================================
 * Main Entry Point for React Application
 * ==============================================================================
 * 
 * This file is the starting point of the React application.
 * It:
 * 1. Creates the React root element
 * 2. Wraps the app with necessary providers
 * 3. Renders the App component
 * 
 * StrictMode:
 * - Activates additional checks and warnings during development
 * - Does not affect production builds
 * - Helps find potential problems early
 * ==============================================================================
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

// Import global styles (Tailwind CSS)
import './index.css';

// Import main App component
import App from './app/App.jsx';

// Create React root and render the application
// document.getElementById('root') is the div in index.html
ReactDOM.createRoot(document.getElementById('root')).render(
  // StrictMode helps identify potential problems in development
  <React.StrictMode>
    {/* BrowserRouter enables client-side routing */}
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
