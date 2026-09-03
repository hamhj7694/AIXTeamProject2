import React from 'react';
import type { CaseRecord } from '../../services/caseApi';
import { actualLossLabel, caseDisplayId, victimStatusLabel, workflowStatusLabel } from '../../utils/casePresentation';

export const CaseContextBar: React.FC<{ item: CaseRecord; compact?: boolean; showProgress?: boolean }> = ({ item, compact = false, showProgress = false }) => {
  const stages = ['상황 접수', '피해 여부 확인', '기관 확인', '보호 조치', '처리 완료'];
  const currentStage = item.status === 'CLOSED' ? 4 : item.transferred === true ? 3 : 1;
  return (
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
    {showProgress && <div className="mt-4 border-t border-slate-100 pt-4"><p className="text-xs font-black text-slate-700">진행 상황</p><div className="mt-3 flex items-start"><div className="flex w-full items-start">{stages.map((stage, index) => <React.Fragment key={stage}><div className="min-w-0 flex-1 text-center"><div className={`mx-auto grid h-6 w-6 place-items-center rounded-full text-[10px] font-black ${index < currentStage ? 'bg-emerald-500 text-white' : index === currentStage ? 'bg-blue-600 text-white ring-4 ring-blue-100' : 'bg-slate-200 text-slate-500'}`}>{index < currentStage ? '✓' : index + 1}</div><p className={`mt-1 text-[10px] font-bold ${index === currentStage ? 'text-blue-700' : 'text-slate-500'}`}>{stage}</p></div>{index < stages.length - 1 && <div className={`mt-3 h-0.5 flex-1 ${index < currentStage ? 'bg-emerald-400' : 'bg-slate-200'}`} />}</React.Fragment>)}</div></div><p className="mt-2 text-[11px] text-slate-500">{currentStage === 1 ? '피해 여부를 확인하고 있습니다.' : currentStage === 3 ? '필요한 보호 조치를 안내하고 있습니다.' : currentStage === 4 ? '사건 처리가 완료되었습니다.' : '현재 상황을 확인하고 있습니다.'}</p></div>}
  </section>
  );
};
