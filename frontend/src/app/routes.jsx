import React, { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import DashboardPage from '../features/dashboard/pages/DashboardPage.jsx';
import StockDetailPage from '../features/stock_view/pages/StockDetailPage.jsx';
import LoginPage from '../features/auth/pages/LoginPage.jsx';
import RequireAuth from '../shared/auth/RequireAuth.jsx';
import LoadingScreen from '../shared/components/LoadingScreen.jsx';

function AppRoutes() {
  return (
    <Suspense fallback={<LoadingScreen message="Loading..." />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <DashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="/stocks/:symbol"
          element={
            <RequireAuth>
              <StockDetailPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default AppRoutes;
