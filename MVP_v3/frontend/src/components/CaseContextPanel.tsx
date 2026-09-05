import React, { useState } from 'react';
import { CheckCircle2, ChevronRight, PanelRightClose, PanelRightOpen, Trash2 } from 'lucide-react';
import type { CaseAction, CaseBundle, CaseFact, CaseSupportSnapshot, CustomerProgressItem, StoredCase, VerificationTask } from '../api/types';
import { CustomerProgressEditor } from './CustomerProgressEditor';
import { ContextEditing, EditableContext } from './EditableContext';
import { ContextWorkspace } from './ContextWorkspace';
import { AdminCaseDialog } from './AdminCaseDialog';
import {
  activeVerifications, caseClaims, caseDemands,
  riskReasons, verificationStatusLabel,
} from '../presentation';

interface Props {
  accessRevision: number;
  onOpenParticipants: () => void;
  caseItem: StoredCase;
  bundle: CaseBundle;
  facts: CaseFact[];
  support: CaseSupportSnapshot | null;
  open: boolean;
  onToggle: () => void;
  onEditVerification: (task: VerificationTask) => void;
  onCreateJudgment: (note: string) => Promise<boolean>;
  onUpdateChecklist: (action: CaseAction, values: { status?: 'REQUESTED' | 'COMPLETED' | 'CANCELLED'; note?: string }) => Promise<boolean>;
  checklistBusy: boolean;
  onProgressSaved: (items: CustomerProgressItem[]) => void;
  onFinalize: (password: string, note: string) => Promise<void>;
  onReopen: (password: string) => Promise<void>;
  onTrash: (password: string) => Promise<void>;
}

const EmptyLine = ({ children }: { children: React.ReactNode }) => <p className="context-empty">{children}</p>;

export const CaseContextPanel: React.FC<Props> = ({ accessRevision, onOpenParticipants, caseItem, bundle, support, open, onToggle, onEditVerification, onProgressSaved, onFinalize, onReopen, onTrash }) => {
  const [adminAction, setAdminAction] = useState<'finalize' | 'reopen' | 'trash' | null>(null);
  const liveContext = support?.available ? support.case_context : null;
  const claims = liveContext?.offender_claims ?? caseClaims(caseItem);
  const demands = liveContext?.offender_demands ?? caseDemands(caseItem);
  const reasons = liveContext?.key_signals ?? riskReasons(caseItem);
  const tactics = liveContext?.manipulation_tactics ?? [];
  const exposure = liveContext?.customer_exposure ?? [];
  const activeTasks = activeVerifications(bundle.verification_tasks ?? []);

  return <><aside className={`context-panel ${open ? 'is-open' : ''}`} aria-label="사건 맥락">
    <div className="context-header"><div><p className="eyebrow">CASE CONTEXT</p><h2>사건 맥락</h2>{liveContext && <small>불러온 사건 정보 기준</small>}</div><button type="button" className="context-open context-header-toggle" onClick={onToggle} aria-expanded={open} aria-controls="case-context-content" title={open ? '사건 맥락 접기' : '사건 맥락 열기'}>{open ? <PanelRightClose size={17}/> : <PanelRightOpen size={17}/>}<span className="sr-only">{open ? '사건 맥락 접기' : '사건 맥락 열기'}</span></button></div>
    <div className="context-scroll" id="case-context-content"><ContextEditing key={caseItem.case_id} caseId={caseItem.case_id}>
      <EditableContext section="SUMMARY" title="현재 사건 요약" lines={[liveContext?.situation_summary || caseItem.diagnosis.context?.summary || '최신 사건 정보 확인 중']} summary/>
      <EditableContext section="EXPOSURE" title="고객 피해·노출 상태" lines={exposure}/>
      <EditableContext section="SIGNAL" title="사기 수법 신호" lines={reasons}/>
      <EditableContext section="CLAIM" title="상대방이 주장한 내용" lines={claims}/>
      <EditableContext section="DEMAND" title="상대방이 요구한 행동" lines={demands}/>
      <EditableContext section="TACTIC" title="압박·조작 수법" lines={tactics}/>
      <ContextWorkspace key={caseItem.case_id} caseId={caseItem.case_id} onOpenParticipants={onOpenParticipants} refreshKey={`${accessRevision}:${bundle.cursor ?? ''}:${String(bundle.case.context_revision ?? '')}:${caseItem.updated_at}:${support?.source_revision ?? ''}`} institutions={<section className="context-section"><h3>기관 확인</h3>{bundle.verification_tasks?.length ? <div className="verification-summary-list">{bundle.verification_tasks.map((task) => <button key={task.verification_task_id} onClick={() => onEditVerification(task)}><span><b>{task.target}</b><small>{verificationStatusLabel(task.status)}</small></span><ChevronRight size={15}/></button>)}</div> : <EmptyLine>등록된 기관 확인이 없습니다.</EmptyLine>}{activeTasks.length > 0 && <p className="context-note">확인 중인 업무 {activeTasks.length}건</p>}</section>}/>
      <details className="context-section"><summary>고객에게 공유할 처리 결과</summary><CustomerProgressEditor key={caseItem.case_id} caseId={caseItem.case_id} items={bundle.customer_progress ?? []} onSaved={onProgressSaved}/></details>
      <details className="context-section"><summary>이전 업무 제안 표시 기록</summary><EditableContext section="NEXT_STEP" title="이전 제안·직원 편집 내용" lines={liveContext?.next_actions ?? []}/></details>
      {caseItem.mode === 'RECOVERY' && <section className="recovery-context"><strong>피해구제 모드</strong><p>추가 송금을 중단하고 지급정지 검토, 112 신고, 증빙 확보와 피해구제 신청을 순서대로 지원하세요.</p></section>}
    </ContextEditing>
      <section className="case-management-section" aria-label="사건 관리">
        <h3>사건 관리</h3>
        <p>관리자 인증 후 사건을 종결하거나 휴지통으로 이동할 수 있습니다.</p>
        <button type="button" className={`case-finalize-button ${caseItem.status === 'CLOSED' || caseItem.mode === 'CLOSED' ? 'is-closed' : ''}`} onClick={() => setAdminAction(caseItem.status === 'CLOSED' || caseItem.mode === 'CLOSED' ? 'reopen' : 'finalize')}><CheckCircle2 size={15}/>{caseItem.status === 'CLOSED' || caseItem.mode === 'CLOSED' ? '사건 다시 진행하기' : '해결 및 종료 처리'}</button>
        <button type="button" className="case-trash-button" onClick={() => setAdminAction('trash')}><Trash2 size={15}/>휴지통으로 보내기</button>
      </section>
    </div>
  </aside>
  {adminAction === 'finalize' && <AdminCaseDialog title="해결 및 종료 처리" description="사건을 해결 상태로 종결합니다. 관리자 암호를 입력해 주세요." confirmLabel="해결 및 종료" noteLabel="종결 메모 (선택)" notePlaceholder="처리 결과나 인계 사항을 기록하세요." onConfirm={onFinalize} onClose={() => setAdminAction(null)}/>}
  {adminAction === 'reopen' && <AdminCaseDialog title="사건 다시 진행하기" description="종결 직전의 사건 상태로 복구합니다. 관리자 암호를 입력해 주세요." confirmLabel="진행 상태로 복구" onConfirm={(password) => onReopen(password)} onClose={() => setAdminAction(null)}/>}
  {adminAction === 'trash' && <AdminCaseDialog title="휴지통으로 보내기" description="사건은 휴지통에서 30일 동안 보관되며 그 안에는 복구할 수 있습니다." confirmLabel="휴지통으로 보내기" onConfirm={(password) => onTrash(password)} onClose={() => setAdminAction(null)}/>}
  </>;
};
