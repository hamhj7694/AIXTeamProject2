import React from 'react';
import type { CaseRecord } from '../../services/caseApi';
import { actualLossLabel, caseDisplayId, victimStatusLabel, workflowStatusLabel } from '../../utils/casePresentation';

export const CaseContextBar: React.FC<{ item: CaseRecord; compact?: boolean }> = ({ item, compact = false }) => (
  <section className={'rounded-2xl border border-slate-200 bg-white shadow-sm ' + (compact ? 'p-3' : 'p-5')}>
    <div className={'grid gap-3 ' + (compact ? 'sm:grid-cols-4 xl:grid-cols-8' : 'sm:grid-cols-2 lg:grid-cols-4')}>
      <div><p className="text-[11px] font-bold text-slate-400">ID</p><p className="mt-1 font-black">{caseDisplayId(item.id)}</p></div>
      <div><p className="text-[11px] font-bold text-slate-400">담당자</p><p className="mt-1 truncate font-bold" title={item.assignee ?? '미배정'}>{item.assignee ?? '미배정'}</p></div>
      <div><p className="text-[11px] font-bold text-slate-400">피해 여부</p><p className="mt-1 font-bold">{victimStatusLabel(item.transferred)}</p></div>
      <div><p className="text-[11px] font-bold text-slate-400">피해 금액</p><p className="mt-1 font-bold">{actualLossLabel(item.amount)}</p></div>
      <div><p className="text-[11px] font-bold text-slate-400">사기 유형</p><p className="mt-1 truncate font-bold" title={item.type}>{item.type || '확인안됨'}</p></div>
      <div><p className="text-[11px] font-bold text-slate-400">업무 진행 상태</p><p className="mt-1 font-bold text-blue-700">{workflowStatusLabel(item.status)}</p></div>
      {!compact && <div><p className="text-[11px] font-bold text-slate-400">최초 생성일</p><p className="mt-1 text-sm font-semibold">{item.createdAt}</p></div>}
      <div><p className="text-[11px] font-bold text-slate-400">최근 업데이트</p><p className="mt-1 text-sm font-semibold">{item.updatedAt}</p></div>
    </div>
  </section>
);
