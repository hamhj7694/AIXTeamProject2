import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { DiagnosisPage } from '../pages/CasePages';
import { BankPage } from '../pages/BankPage';
import { CustomerPage } from '../pages/CustomerPage';
import { CaseEntryPageV2 } from '../pages/CaseEntryPageV2';
import { CaseVerificationPage } from '../pages/CaseVerificationPage';
import { CasesTablePage } from '../pages/CasesTablePage';

export const AppRoutes: React.FC = () => <Router><Routes>
  <Route path="/" element={<DiagnosisPage />} />
  <Route path="/cases" element={<CasesTablePage />} />
  <Route path="/cases/:caseId" element={<CaseEntryPageV2 />} />
  <Route path="/cases/:caseId/customer" element={<CustomerPage />} />
  <Route path="/cases/:caseId/bank" element={<BankPage />} />
  <Route path="/cases/:caseId/verify" element={<CaseVerificationPage />} />
</Routes></Router>;
