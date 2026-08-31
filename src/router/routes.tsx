import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { BankPage, CaseEntryPage, CustomerPage, DiagnosisPage, VerifyPage } from '../pages/CasePages';
import { CasesTablePage } from '../pages/CasesTablePage';

export const AppRoutes: React.FC = () => <Router><Routes>
  <Route path="/" element={<DiagnosisPage />} />
  <Route path="/cases" element={<CasesTablePage />} />
  <Route path="/cases/:caseId" element={<CaseEntryPage />} />
  <Route path="/cases/:caseId/customer" element={<CustomerPage />} />
  <Route path="/cases/:caseId/bank" element={<BankPage />} />
  <Route path="/verify/:token" element={<VerifyPage />} />
</Routes></Router>;
