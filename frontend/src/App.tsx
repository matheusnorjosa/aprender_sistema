import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import StatusPage from './pages/StatusPage';
import ReportsConflitos from './pages/ReportsConflitos';
import ReportsWorkload from './pages/ReportsWorkload';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path='/dashboard' element={<Dashboard />} />
        <Route path='/reports/conflitos' element={<ReportsConflitos />} />
        <Route path='/reports/workload' element={<ReportsWorkload />} />
        <Route path='/status' element={<StatusPage />} />
        <Route path='/' element={<Navigate to='/dashboard' replace />} />
        <Route path='*' element={<Navigate to='/dashboard' replace />} />
      </Routes>
    </Router>
  );
}
// HMR 10/06/2025 15:06:10
// HMR 10/06/2025 15:06:37
