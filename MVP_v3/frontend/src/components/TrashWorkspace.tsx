import React, { useState } from 'react';
import { AlertCircle, ArchiveRestore, RotateCcw, Trash2, X } from 'lucide-react';
import type { StoredCase } from '../api/types';
import { incidentTitle } from '../presentation';
import { AdminCaseDialog } from './AdminCaseDialog';

interface Props {
  cases: StoredCase[];
  loading: boolean;
  error: string;
  onRetry: () => void;
  onClose: () => void;
  onRestore: (caseId: string, password: string) => Promise<void>;
  onPurge: (caseId: string, password: string) => Promise<void>;
}

type TrashAction = { type: 'restore' | 'purge'; item: StoredCase } | null;

const daysUntilPurge = (item: StoredCase) => {
  if (!item.trash_expires_at) return 30;
  return Math.max(0, Math.ceil((new Date(item.trash_expires_at).getTime() - Date.now()) / 86_400_000));
};

export const TrashWorkspace: React.FC<Props> = ({ cases, loading, error, onRetry, onClose, onRestore, onPurge }) => {
  const [action, setAction] = useState<TrashAction>(null);
  return <section className="trash-workspace">
    <header><div><span><Trash2 size={20}/></span><div><p className="eyebrow">CASE TRASH</p><h1>휴지통</h1><small>휴지통으로 보낸 사건은 30일 동안 보관된 뒤 자동 삭제됩니다.</small></div></div><button type="button" className="icon-button" onClick={onClose} aria-label="휴지통 닫기"><X size={19}/></button></header>
    <div className="trash-workspace-body">
      {loading && <div className="trash-workspace-state"><span className="case-skeleton"/><span className="case-skeleton"/></div>}
      {!loading && error && <div className="trash-workspace-state error"><AlertCircle size={24}/><strong>휴지통을 불러오지 못했습니다.</strong><span>{error}</span><button type="button" onClick={onRetry}>다시 시도</button></div>}
      {!loading && !error && cases.length === 0 && <div className="trash-workspace-state"><ArchiveRestore size={34}/><strong>휴지통이 비어 있습니다.</strong><span>사건 맥락 하단의 ‘휴지통으로 보내기’를 사용하면 이곳에서 복구하거나 영구 삭제할 수 있습니다.</span></div>}
      {!loading && !error && cases.length > 0 && <div className="trash-workspace-grid">{cases.map((item) => <article className="trash-workspace-card" key={item.case_id}>
        <header><div><b>{item.case_id}</b><h2>{incidentTitle(item)}</h2></div><span>{daysUntilPurge(item)}일 남음</span></header>
        <p>{item.initial_brief}</p>
        <dl><div><dt>휴지통 이동</dt><dd>{item.deleted_at ? new Date(item.deleted_at).toLocaleString('ko-KR') : '확인 중'}</dd></div><div><dt>자동 삭제 예정</dt><dd>{item.trash_expires_at ? new Date(item.trash_expires_at).toLocaleString('ko-KR') : '30일 후'}</dd></div></dl>
        <footer><button type="button" className="trash-restore-action" onClick={() => setAction({ type: 'restore', item })}><RotateCcw size={14}/>복구</button><button type="button" className="trash-purge-action" onClick={() => setAction({ type: 'purge', item })}><Trash2 size={14}/>즉시 영구 삭제</button></footer>
      </article>)}</div>}
    </div>
    {action?.type === 'restore' && <AdminCaseDialog title="휴지통에서 복구" description={`${action.item.case_id} 사건을 현재 대응 사건 목록으로 복구합니다.`} confirmLabel="복구" onConfirm={(password) => onRestore(action.item.case_id, password)} onClose={() => setAction(null)}/>}
    {action?.type === 'purge' && <AdminCaseDialog title="사건 즉시 영구 삭제" description={`${action.item.case_id} 사건을 지금 영구 삭제합니다. 이 작업은 되돌릴 수 없습니다.`} confirmLabel="영구 삭제" danger onConfirm={(password) => onPurge(action.item.case_id, password)} onClose={() => setAction(null)}/>}
  </section>;
};
