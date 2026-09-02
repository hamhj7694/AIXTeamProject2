import React from 'react';
import { AppLayout } from '../components/layout/AppLayout';

export const ResponseGuidePage: React.FC = () => {
  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-bold mb-6">상황별 대응</h2>
        <p className="text-gray-600">상황별 대응 안내가 여기에 표시됩니다.</p>
      </div>
    </AppLayout>
  );
};
