import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { DiagnosisPage } from '../pages/DiagnosisPage';
import { BankCollaborationPage } from '../pages/BankCollaborationPage';
import { CustomerChatPage } from '../pages/CustomerChatPage';
import { CaseEntryPageV2 } from '../pages/CaseEntryPageV2';
import { CaseVerificationPage } from '../pages/CaseVerificationPage';
import { CasesTablePage } from '../pages/CasesTablePage';

export const AppRoutes: React.FC = () => <Router><Routes>
  <Route path="/" element={<DiagnosisPage />} />
  <Route path="/cases" element={<CasesTablePage />} />
  <Route path="/cases/:caseId" element={<CaseEntryPageV2 />} />
  <Route path="/cases/:caseId/customer" element={<CustomerChatPage />} />
  <Route path="/cases/:caseId/bank" element={<BankCollaborationPage />} />
  <Route path="/cases/:caseId/verify" element={<CaseVerificationPage />} />
</Routes></Router>;
