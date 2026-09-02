import React from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { SafetyChat } from '../features/consultation/components/SafetyChat';

export const ConsultationPage: React.FC = () => {
  return (
    <AppLayout>
      <SafetyChat />
    </AppLayout>
  );
};
