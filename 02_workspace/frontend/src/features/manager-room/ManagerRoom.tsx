import React from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { ManagerRoomHeader } from './components/ManagerRoomHeader';
import { ManagerRoomNavigation } from './components/ManagerRoomNavigation';
import { ManagerRoomViewPlaceholder } from './components/ManagerRoomViewPlaceholder';
import { AiWorkspace } from './components/workspace/AiWorkspace';
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
    <AppLayout>
      <div className="mx-auto max-w-6xl py-6 lg:ml-64 lg:py-8">
        <ManagerRoomHeader
          caseInfo={caseInfo}
          customerViewActive={currentView === 'customer'}
          onOpenCustomerView={() => handleViewChange('customer')}
        />
        <ManagerRoomNavigation
          currentView={currentView}
          onViewChange={handleViewChange}
        />

        <div className="py-5">
          {currentView === 'workspace' ? (
            <AiWorkspace onOpenCustomerView={() => handleViewChange('customer')} />
          ) : (
            <ManagerRoomViewPlaceholder view={currentView} />
          )}
        </div>
      </div>
    </AppLayout>
  );
};
