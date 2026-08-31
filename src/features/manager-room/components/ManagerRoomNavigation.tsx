import React from 'react';
import { cn } from '../../../utils/helpers';
import { ManagerRoomView } from '../types';

interface ManagerRoomNavigationProps {
  currentView: ManagerRoomView;
  onViewChange: (view: ManagerRoomView) => void;
}

const navigationItems: Array<{
  view: Exclude<ManagerRoomView, 'customer'>;
  label: string;
}> = [
  { view: 'workspace', label: 'AI 사건 워크스페이스' },
  { view: 'progress', label: '사건 진행 흐름' },
  { view: 'evidence', label: '원본 Evidence' },
];

export const ManagerRoomNavigation: React.FC<ManagerRoomNavigationProps> = ({
  currentView,
  onViewChange,
}) => {
  return (
    <nav aria-label="담당자 ROOM 화면" className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 sm:px-6 lg:px-8">
        {navigationItems.map((item) => {
          const active = currentView === item.view;

          return (
            <button
              key={item.view}
              type="button"
              onClick={() => onViewChange(item.view)}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'whitespace-nowrap border-b-2 px-4 py-4 text-sm font-semibold transition-colors',
                active
                  ? 'border-slate-900 text-slate-950'
                  : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
              )}
            >
              {item.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
