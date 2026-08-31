import React from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { ManagerRoomHeader } from './components/ManagerRoomHeader';
import { ManagerRoomNavigation } from './components/ManagerRoomNavigation';
import { ManagerRoomViewPlaceholder } from './components/ManagerRoomViewPlaceholder';
import { createManagerRoomCaseMock } from './data/managerRoomMock';
import { isManagerRoomView, ManagerRoomView } from './types';

export const ManagerRoom: React.FC = () => {
  const { caseId = 'UNKNOWN-CASE' } = useParams<{ caseId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const requestedView = searchParams.get('view');
  const currentView: ManagerRoomView = isManagerRoomView(requestedView)
    ? requestedView
    : 'workspace';
  const caseInfo = createManagerRoomCaseMock(caseId);

  const handleViewChange = (view: ManagerRoomView) => {
    const nextSearchParams = new URLSearchParams(searchParams);

    // 기본 화면은 query를 생략해 최초 진입 URL을 간결하게 유지한다.
    if (view === 'workspace') {
      nextSearchParams.delete('view');
    } else {
      nextSearchParams.set('view', view);
    }

    setSearchParams(nextSearchParams);
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <ManagerRoomHeader
        caseInfo={caseInfo}
        customerViewActive={currentView === 'customer'}
        onOpenCustomerView={() => handleViewChange('customer')}
      />
      <ManagerRoomNavigation
        currentView={currentView}
        onViewChange={handleViewChange}
      />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <ManagerRoomViewPlaceholder view={currentView} />
      </main>
    </div>
  );
};
