import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConsultationPage } from '../pages/ConsultationPage';
import { HistoryPage } from '../pages/HistoryPage';
import { HistoryDetailPage } from '../pages/HistoryDetailPage';
import { SafetyGuidePage } from '../pages/SafetyGuidePage';
import { ResponseGuidePage } from '../pages/ResponseGuidePage';
import { ManagerRoomPage } from '../pages/ManagerRoomPage';

export const AppRoutes: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ConsultationPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/history/:id" element={<HistoryDetailPage />} />
        <Route path="/safety" element={<SafetyGuidePage />} />
        <Route path="/response-guide" element={<ResponseGuidePage />} />
        <Route path="/cases/:caseId/bank" element={<ManagerRoomPage />} />
      </Routes>
    </Router>
  );
};
