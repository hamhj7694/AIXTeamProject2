import React from 'react';
import { AppLayout } from '../components/layout/AppLayout';

export const HistoryPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-bold mb-6">상담 기록</h2>
        <p className="text-gray-600">상담 기록이 여기에 표시됩니다.</p>
      </div>
    </AppLayout>
  );
};
