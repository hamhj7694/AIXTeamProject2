import React, { useState } from 'react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { cn } from '../../../../utils/helpers';
import { ManagerRoomChecklistItem } from '../../types';

interface InvestigationChecklistProps {
  initialItems: ManagerRoomChecklistItem[];
}

export const InvestigationChecklist: React.FC<
  InvestigationChecklistProps
> = ({ initialItems }) => {
  const [items, setItems] = useState(initialItems);
  const completedCount = items.filter((item) => item.completed).length;

  const toggleItem = (itemId: string) => {
    // 체크 여부는 담당자가 직접 바꾸며 Backend에는 저장하지 않는다.
    setItems((currentItems) =>
      currentItems.map((item) =>
        item.id === itemId ? { ...item, completed: !item.completed } : item
      )
    );
  };

  return (
    <Card className="rounded-xl border-slate-200 p-4 shadow-sm">
      <section aria-labelledby="investigation-checklist-title">
        <div className="flex items-center justify-between gap-3">
          <h2 id="investigation-checklist-title" className="text-base font-extrabold text-slate-950">
            조사 체크리스트
          </h2>
          <Badge variant="success">
            {completedCount}/{items.length} 확인
          </Badge>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          담당자가 직접 확인한 상태입니다.
        </p>

        <div className="mt-3 space-y-1.5">
          {items.map((item) => (
            <label
              key={item.id}
              className={cn(
                'flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 transition',
                item.completed
                  ? 'border-emerald-100 bg-emerald-50/50 hover:border-emerald-200'
                  : 'border-slate-200 bg-white hover:border-blue-200 hover:bg-blue-50/30'
              )}
            >
              <input
                type="checkbox"
                checked={item.completed}
                onChange={() => toggleItem(item.id)}
                className={cn(
                  'mt-0.5 h-4 w-4 rounded border-slate-300',
                  item.completed
                    ? 'text-emerald-600 focus:ring-emerald-500'
                    : 'text-blue-600 focus:ring-blue-500'
                )}
              />
              <span
                className={cn(
                  'text-sm font-semibold leading-5',
                  item.completed ? 'text-emerald-900' : 'text-slate-700'
                )}
              >
                {item.label}
              </span>
            </label>
          ))}
        </div>

        <p className="mt-2 text-[11px] leading-5 text-slate-400">
          현재 브라우저 화면에서만 유지되는 Local state입니다.
        </p>
      </section>
    </Card>
  );
};
