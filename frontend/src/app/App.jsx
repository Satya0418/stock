import React from 'react';

import AppRoutes from './routes.jsx';
import ErrorBoundary from '../shared/components/ErrorBoundary.jsx';

function App() {
  return (
    <ErrorBoundary>
      <AppRoutes />
    </ErrorBoundary>
  );
}

export default App;
