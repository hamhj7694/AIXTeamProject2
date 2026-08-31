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
    <nav
      aria-label="담당자 ROOM 화면"
      className="-mt-px rounded-b-xl border border-slate-200 bg-white"
    >
      <div className="flex gap-1 overflow-x-auto px-2 sm:px-3">
        {navigationItems.map((item) => {
          const active = currentView === item.view;

          return (
            <button
              key={item.view}
              type="button"
              onClick={() => onViewChange(item.view)}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'whitespace-nowrap border-b-2 px-3 py-3 text-xs font-bold transition-colors sm:text-sm',
                active
                  ? 'border-blue-600 text-blue-700'
                  : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-900'
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
