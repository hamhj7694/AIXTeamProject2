import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, CircleDot, Download, FilePlus2, FileText, MessageSquare, Pencil, RotateCcw, Trash2, UsersRound, X } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CaseLiveLog } from '../features/mvp-chat/CaseLiveLog';
import { ChatWorkspace } from '../features/mvp-chat/ChatWorkspace';
import { createDraftWorkCard, getBankWorkCardActions } from '../features/mvp-chat/work-cards/catalog';
import { WorkCardRenderer } from '../features/mvp-chat/work-cards/WorkCardRenderer';
import type { WorkCardDescriptor, WorkCardType } from '../features/mvp-chat/work-cards/types';
import { useCaseSyncRefresh } from '../features/case-sync/useCaseSyncRefresh';
import { caseWorkflowApi } from '../services/caseWorkflowApi';
import { caseApi, type CaseDetail } from '../services/caseApi';
import { mvpChatApi, type CaseBundleV2, type CaseMember, type CasePresence, type CaseSupportSnapshot, type MessageChannel, type MvpMessage } from '../services/mvpChatApi';

const currentUser = { user_id: 'mvp-v2-current-user', display_name: '현재 사용자', role: 'CHAT_OPERATOR' as const };
type BankView = 'COLLABORATION' | 'CUSTOMER' | 'AI_PRIVATE';
const meta: Record<BankView, { label: string; description: string; presenceChannel: MessageChannel }> = {
  COLLABORATION: { label: '은행 협업', description: '팀 대화와 팀에 공유된 AI 답변을 함께 확인합니다.', presenceChannel: 'TEAM' },
  CUSTOMER: { label: '고객 대화', description: '고객에게 전달하는 메시지 채널입니다.', presenceChannel: 'CUSTOMER' },
  AI_PRIVATE: { label: 'AI 개인 작업공간', description: 'CaseCopilot에게 분석·질문 초안을 비공개로 요청합니다. 필요한 답변만 팀에 공유하세요.', presenceChannel: 'AI_INTERNAL' },
};
const role: Record<CaseMember['role'], string> = { CASE_OWNER: '메인 담당자', CHAT_OPERATOR: '채팅 담당자', REVIEWER: '검토자', VIEWER: '열람자' };
const escapeHtml = (text: string) => text.replace(/[&<>]/g, (value) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[value] ?? value));
type ArchiveReport = { id: string; title: string; type: '일반' | '최종'; createdAt: string; html: string; deletedAt?: string };
const archiveKey = (caseId: string) => `mvp-v2:reports:${caseId}`;
const readReports = (caseId: string): ArchiveReport[] => {
  try { return (JSON.parse(localStorage.getItem(archiveKey(caseId)) ?? '[]') as ArchiveReport[]).filter((item) => !item.deletedAt || Date.now() - new Date(item.deletedAt).getTime() < 30 * 86400000); } catch { return []; }
};
const writeReports = (caseId: string, reports: ArchiveReport[]) => localStorage.setItem(archiveKey(caseId), JSON.stringify(reports));

const known = (value: unknown, fallback = '확인안됨') => {
  if (value === null || value === undefined || value === '') return fallback;
  return String(value);
};

const buildStructuredReportHtml = (input: {
  caseId: string;
  type: ArchiveReport['type'];
  brief: string;
  currentCase: Record<string, unknown>;
  members: CaseMember[];
  facts: import('../services/mvpChatApi').CaseFact[];
  verifications: CaseBundleV2['verification_tasks'];
  nextTasks: string[];
  eventCount: number;
}) => {
  const owner = input.members.find((member) => member.role === 'CASE_OWNER');
  const confirmedFacts = input.facts.filter((fact) => fact.status === 'CONFIRMED');
  const pendingFacts = input.facts.filter((fact) => fact.status !== 'CONFIRMED');
  const completedVerifications = input.verifications.filter((task) => task.status === 'COMPLETED' || task.status === 'FAILED');
  const pendingVerifications = input.verifications.filter((task) => task.status !== 'COMPLETED' && task.status !== 'FAILED');
  const summary = input.brief.trim() || '현재까지 확인된 사건 정보를 바탕으로 추가 확인이 필요합니다.';
  const conclusion = completedVerifications.length
    ? '확인된 검증 결과와 고객 피해 정보를 기준으로 보호 조치 및 후속 대응을 진행해야 합니다.'
    : '기관 검증과 고객 피해 여부 확인이 완료되지 않아 현 단계에서는 추가 사실 확인이 필요합니다.';
  const list = (items: string[], empty: string) => items.length ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : `<p class="empty">${escapeHtml(empty)}</p>`;

  return `<!doctype html><html><head><meta charset="utf-8"><title>Case ${escapeHtml(input.caseId)} 종합 보고서</title><style>body{font-family:Arial,sans-serif;max-width:860px;margin:48px auto;color:#172033;line-height:1.7}h1{border-bottom:3px solid #111827;padding-bottom:14px}h2{margin-top:30px;font-size:18px}.meta,.empty{color:#64748b}.summary{border-left:5px solid #2563eb;background:#eff6ff;border-radius:10px;padding:18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.item{border:1px solid #dbe2ea;border-radius:10px;padding:12px}.label{display:block;color:#64748b;font-size:12px}.value{font-weight:700}.note{margin-top:30px;border-top:1px solid #dbe2ea;padding-top:14px;color:#64748b;font-size:12px}@media(max-width:640px){.grid{grid-template-columns:1fr}}</style></head><body><h1>Case ${escapeHtml(input.caseId)} ${input.type === '최종' ? '최종' : '종합'} 보고서</h1><p class="meta">작성 시각 ${new Date().toLocaleString('ko-KR')} · 구조화된 Case 정보를 기준으로 작성</p><h2>1. 사건 종합 요약</h2><div class="summary">${escapeHtml(summary)}</div><h2>2. 사건 기본 정보</h2><div class="grid"><div class="item"><span class="label">업무 진행 상태</span><span class="value">${escapeHtml(known(input.currentCase.workflow_status ?? input.currentCase.status))}</span></div><div class="item"><span class="label">메인 담당자</span><span class="value">${escapeHtml(owner?.display_name ?? '미배정')}</span></div><div class="item"><span class="label">피해 여부</span><span class="value">${escapeHtml(known(input.currentCase.victim_transfer_status))}</span></div><div class="item"><span class="label">확인 피해 금액</span><span class="value">${escapeHtml(known(input.currentCase.actual_loss_amount_krw))}</span></div><div class="item"><span class="label">사기 유형</span><span class="value">${escapeHtml(known(input.currentCase.fraud_type))}</span></div><div class="item"><span class="label">참여 인원</span><span class="value">${input.members.length}명</span></div></div><h2>3. 확인된 핵심 정보</h2>${list(confirmedFacts.map((fact) => `${fact.field}: ${fact.value} (${fact.confirmed_by ?? '담당자'} 확인)`), '담당자가 확정한 CaseFact가 없습니다.')}<h2>4. 기관 검증 결과</h2>${list(completedVerifications.map((task) => `${task.target}: ${task.result_summary || task.claim} · 확인자 ${task.verified_by || '확인안됨'} · 출처 ${task.rag_source || '확인안됨'}`), '완료된 기관 검증 결과가 없습니다.')}<h2>5. 미확인 사항</h2>${list([...pendingFacts.map((fact) => `${fact.field}: ${fact.value}`), ...pendingVerifications.map((task) => `${task.target}: ${task.claim}`)], '현재 등록된 미확인 사항이 없습니다.')}<h2>6. 권고 대응 및 다음 작업</h2><p>${escapeHtml(conclusion)}</p>${list(input.nextTasks, '추가로 등록된 우선 작업이 없습니다.')}<h2>7. 처리 현황</h2><p>보고서 작성 시점까지 의미 있는 업무 이벤트 ${input.eventCount}건이 Case에 반영되었습니다. 채팅·로그 원문은 본 보고서에 그대로 복제하지 않으며, 필요한 근거는 원본 Case 기록에서 확인합니다.</p><p class="note">이 보고서는 현재 구조화 데이터 기반 Frontend 초안입니다. AI 보고서 엔진 연결 후 동일 항목을 유지하면서 문장 구성과 종합 판단을 고도화합니다.</p></body></html>`;
};

export const BankCollaborationPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const navigate = useNavigate();
  const [view, setView] = useState<BankView>('COLLABORATION');
  const [bundle, setBundle] = useState<CaseBundleV2 | null>(null);
  const [messages, setMessages] = useState<MvpMessage[]>([]);
  const [members, setMembers] = useState<CaseMember[]>([]);
  const [presence, setPresence] = useState<CasePresence[]>([]);
  const [modal, setModal] = useState<'participants' | 'assignee' | 'close' | null>(null);
  const [assigneeDraft, setAssigneeDraft] = useState('');
  const [focusMessageId, setFocusMessageId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [screen, setScreen] = useState<'work' | 'reports' | 'trash' | 'document'>('work');
  const [reports, setReports] = useState<ArchiveReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<ArchiveReport | null>(null);
  const [sharingMessageId, setSharingMessageId] = useState<string | null>(null);
  const [facts, setFacts] = useState<import('../services/mvpChatApi').CaseFact[]>([]);
  const [activeCard, setActiveCard] = useState<WorkCardDescriptor | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [caseSupport, setCaseSupport] = useState<CaseSupportSnapshot | null>(null);

  const load = useCallback(async () => {
    const selectedChannel: MessageChannel | undefined = view === 'CUSTOMER' ? 'CUSTOMER' : undefined;
    const [nextBundle, allMessages, nextMembers, nextPresence, nextFacts, nextCaseDetail, nextCaseSupport] = await Promise.all([
      mvpChatApi.getBundle(caseId, 'bank'),
      mvpChatApi.listMessages(caseId, selectedChannel),
      mvpChatApi.listMembers(caseId),
      mvpChatApi.listPresence(caseId),
      mvpChatApi.listCaseFacts(caseId),
      caseApi.get(caseId),
      mvpChatApi.getCaseSupportSnapshot(caseId).catch(() => null),
    ]);
    const nextMessages = view === 'COLLABORATION'
      ? allMessages.filter((message) => message.channel === 'TEAM' || (message.message_kind === 'AI_RESPONSE' && message.visibility === 'BANK_INTERNAL'))
      : view === 'AI_PRIVATE'
        ? allMessages.filter((message) => message.channel === 'AI_INTERNAL' && (
          message.actor_user_id === currentUser.user_id
          || message.private_owner_user_id === currentUser.user_id
          || (message.message_kind === 'SYSTEM_EVENT' && message.private_owner_user_id === null)
        ))
        : allMessages;
    setBundle(nextBundle); setMessages(nextMessages); setMembers(nextMembers); setPresence(nextPresence); setFacts(nextFacts); setCaseDetail(nextCaseDetail); setCaseSupport(nextCaseSupport);
  }, [caseId, view]);
  useCaseSyncRefresh(caseId, load);
  useEffect(() => { mvpChatApi.upsertMember(caseId, currentUser).then(() => load()).catch((reason) => setError(reason instanceof Error ? reason.message : '은행 협업 화면을 불러오지 못했습니다.')); }, [caseId, load]);
  useEffect(() => { load().catch(() => undefined); }, [view, load]);
  useEffect(() => { const beat = () => mvpChatApi.heartbeat(caseId, { ...currentUser, presence: 'VIEWING', channel: meta[view].presenceChannel }).then(() => load()).catch(() => undefined); void beat(); const timer = window.setInterval(beat, 10_000); return () => window.clearInterval(timer); }, [caseId, view, load]);
  useEffect(() => { setReports(readReports(caseId)); }, [caseId]);

  const currentCase: Record<string, unknown> = { ...(bundle?.case ?? {}), fraud_type: caseDetail?.type, summary: caseDetail?.summary };
  const brief = caseSupport?.case_brief?.summary ?? String(currentCase.initial_brief ?? 'Case 정보를 불러오는 중입니다.');
  const unresolvedItems = caseSupport?.unresolved_items ?? [];
  const risks = (bundle?.verification_tasks ?? []).filter((item) => item.status !== 'COMPLETED');
  const owner = members.find((member) => member.role === 'CASE_OWNER');
  const emergencyAlertMessage = [...(bundle?.recent_messages ?? [])].reverse().find((message) =>
    message.channel === 'AI_INTERNAL'
    && message.message_kind === 'SYSTEM_EVENT'
    && message.actor_display_name === 'CaseCopilot 긴급 알림');
  const nextTasks = [
    !owner ? '메인 담당자를 배정해 주세요.' : null,
    currentCase.victim_transfer_status === 'UNKNOWN' ? '고객 상담에서 피해 여부와 실제 피해액을 확인해 주세요.' : null,
    currentCase.status !== 'CLOSED' && risks.length === 0 ? '기관 검증 화면에서 사칭 주장에 대한 확인 요청을 남겨 주세요.' : null,
    ...unresolvedItems.map((item) => `AI 확인 필요 (${item.priority}): ${item.description}`),
  ].filter((value): value is string => Boolean(value));
  const onlineCount = useMemo(() => presence.filter((item) => item.presence === 'VIEWING' || item.presence === 'TYPING').length, [presence]);
  const visibleReports = reports.filter((item) => !item.deletedAt);
  const trashedReports = reports.filter((item) => item.deletedAt);
  const persistReports = (next: ArchiveReport[]) => { setReports(next); writeReports(caseId, next); };

  const createReport = async (type: ArchiveReport['type'] = '일반') => {
    const report: ArchiveReport = {
      id: crypto.randomUUID(),
      title: type === '최종' ? '최종 종합 보고서' : `Case 종합 보고서 ${visibleReports.length + 1}`,
      type,
      createdAt: new Date().toISOString(),
      html: buildStructuredReportHtml({ caseId, type, brief, currentCase, members, facts, verifications: bundle?.verification_tasks ?? [], nextTasks, eventCount: bundle?.recent_events.length ?? 0 }),
    };
    persistReports([report, ...reports]); setSelectedReport(report); setScreen('document');
    try {
      const notice = await mvpChatApi.createMessage(caseId, {
        actor_type: 'BANK_AGENT', actor_user_id: 'case-copilot', actor_display_name: 'CaseCopilot', actor_role: null,
        content: `${report.title}가 생성되었습니다. 보고서 보기에서 내용을 확인할 수 있습니다.`,
        channel: 'TEAM', audience: 'BANK_INTERNAL', visibility: 'BANK_INTERNAL', message_kind: 'SYSTEM_EVENT',
      });
      if (view === 'COLLABORATION') setMessages((items) => [...items, notice]);
    } catch {
      setError('보고서는 생성되었지만 은행 협업 알림을 남기지 못했습니다.');
    }
  };
  const moveReportToTrash = (reportId: string) => persistReports(reports.map((item) => item.id === reportId ? { ...item, deletedAt: new Date().toISOString() } : item));
  const restoreReport = (reportId: string) => persistReports(reports.map((item) => item.id === reportId ? { ...item, deletedAt: undefined } : item));
  const removeReportPermanently = (reportId: string) => persistReports(reports.filter((item) => item.id !== reportId));
  const downloadWord = () => { if (!selectedReport) return; const blob = new Blob([selectedReport.html], { type: 'application/msword;charset=utf-8' }); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `Case-${caseId}-report.doc`; link.click(); URL.revokeObjectURL(link.href); };
  const printPdf = () => { if (!selectedReport) return; const popup = window.open('', '_blank'); if (!popup) return; popup.document.write(selectedReport.html); popup.document.close(); popup.focus(); popup.print(); };
  const closeCase = async () => { try { await caseWorkflowApi.finalizeReport(caseId, Number(currentCase.version ?? 1), '사건 종료 시 최종 보고서 생성'); await load(); await createReport('최종'); setModal(null); } catch (reason) { setError(reason instanceof Error ? reason.message : '사건을 종료하지 못했습니다.'); } };
  const uploadFile = (file: File) => mvpChatApi.uploadAttachment(caseId, file, currentUser.display_name, view === 'CUSTOMER' ? 'CUSTOMER' : view === 'AI_PRIVATE' ? 'AI_PRIVATE' : 'BANK_INTERNAL');
  const send = async (content: string, attachmentIds: string[] = []) => {
    setSending(true);
    try {
      if (view === 'AI_PRIVATE') {
        const request = await mvpChatApi.createMessage(caseId, { actor_type: 'BANK_STAFF', actor_user_id: currentUser.user_id, actor_display_name: currentUser.display_name, actor_role: currentUser.role, content, channel: 'AI_INTERNAL', audience: 'BANK_INTERNAL', visibility: 'AI_PRIVATE', message_kind: 'AI_REQUEST', attachment_ids: attachmentIds });
        if (!content) { setMessages((items) => [...items, request]); return; }
        const reply = await mvpChatApi.invokeCopilot(caseId, content, 'AI_INTERNAL', currentUser);
        setMessages((items) => [...items, request, reply]);
        return;
      }
      const channel: MessageChannel = view === 'CUSTOMER' ? 'CUSTOMER' : 'TEAM';
      const customerVisible = channel === 'CUSTOMER';
      const created = await mvpChatApi.createMessage(caseId, { actor_type: 'BANK_STAFF', actor_user_id: currentUser.user_id, actor_display_name: currentUser.display_name, actor_role: currentUser.role, content, channel, audience: customerVisible ? 'CUSTOMER' : 'BANK_INTERNAL', visibility: customerVisible ? 'CUSTOMER' : 'BANK_INTERNAL', message_kind: 'CHAT', mentions: channel === 'TEAM' && /@CaseCopilot\b/i.test(content) ? ['CaseCopilot'] : [], attachment_ids: attachmentIds });
      if (channel === 'TEAM' && /@CaseCopilot\b/i.test(content)) {
        const reply = await mvpChatApi.invokeCopilot(caseId, content, 'TEAM', currentUser);
        setMessages((items) => [...items, created, reply]);
        return;
      }
      setMessages((items) => [...items, created]);
    } finally { setSending(false); }
  };
  const shareAiMessage = async (message: MvpMessage) => { setSharingMessageId(message.message_id); try { await mvpChatApi.shareAiMessage(caseId, message.message_id, currentUser); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : 'AI 답변을 팀에 공유하지 못했습니다.'); } finally { setSharingMessageId(null); } };
  const openWorkCard = (cardType: WorkCardType) => setActiveCard(createDraftWorkCard(cardType));
  const handleQuickAction = (actionId: string) => openWorkCard(actionId as WorkCardType);
  const goToMessage = (messageId: string, sourceChannel?: string) => { if (sourceChannel) setView(sourceChannel === 'CUSTOMER' ? 'CUSTOMER' : sourceChannel === 'AI_INTERNAL' ? 'AI_PRIVATE' : 'COLLABORATION'); setFocusMessageId(messageId); window.setTimeout(() => setFocusMessageId(null), 1500); };
  useEffect(() => {
    const openBookmark = (event: Event) => {
      const detail = (event as CustomEvent<{ target_id?: string; channel?: string }>).detail;
      if (!detail?.target_id) return;
      goToMessage(detail.target_id, detail.channel);
    };
    window.addEventListener('mvp-bookmark-open', openBookmark);
    return () => window.removeEventListener('mvp-bookmark-open', openBookmark);
  }, []);
  const stateLabel = (state?: string) => state === 'VIEWING' || state === 'TYPING' ? '접속/열람 중' : '부재중';

  return <AppLayout><main className="mx-auto max-w-[1440px] py-6 lg:ml-64"><div className="mb-4 flex items-center justify-between gap-3"><Link to={`/cases/${caseId}`} className="inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> Case로 돌아가기</Link><button onClick={() => setModal('close')} className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-bold text-rose-700">사건 종료하기</button></div><section className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex min-w-0 flex-wrap items-center gap-2"><h1 className="text-lg font-black">{String(currentCase.case_id ?? caseId).replace(/^VP-/, '#')}</h1><p className="min-w-[200px] flex-1 truncate text-xs text-slate-500">{brief}</p><button onClick={() => { if (screen === 'work') { setReports(readReports(caseId)); setScreen('reports'); } else { setScreen('work'); setSelectedReport(null); } }} className="ml-auto inline-flex items-center gap-1 rounded-xl bg-slate-900 px-3 py-2 text-xs font-bold text-white">{screen === 'work' ? <FileText size={15}/> : <MessageSquare size={15}/>} {screen === 'work' ? '보고서 보기' : '채팅 보기'}</button></div><div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3"><UsersRound size={16} className="text-blue-600"/><button onClick={() => setModal('participants')} className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-700">참여자 {members.length}명 보기</button><span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-bold text-blue-700">메인 담당자 {owner?.display_name ?? '미배정'}</span><span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700"><CircleDot size={13}/> 열람 중 {onlineCount}명</span><button onClick={() => { setAssigneeDraft(owner?.display_name ?? ''); setModal('assignee'); }} className="ml-auto inline-flex items-center gap-1 rounded-xl bg-slate-900 px-3 py-2 text-xs font-bold text-white"><Pencil size={13}/>담당자 배정</button></div></section>{error && <p className="mb-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
  {screen === 'reports' && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><h2 className="mr-auto text-lg font-black">보고서 목록</h2><button onClick={() => setScreen('trash')} className="rounded-xl border px-3 py-2 text-xs font-bold">휴지통 {trashedReports.length}</button><button onClick={() => void createReport()} className="inline-flex items-center gap-1 rounded-xl bg-slate-900 px-3 py-2 text-xs font-bold text-white"><FilePlus2 size={14}/>새 보고서 만들기</button></div><div className="mt-4 space-y-2">{visibleReports.length ? visibleReports.map((item) => <div key={item.id} className="flex items-center gap-3 rounded-xl border p-3"><button onClick={() => { setSelectedReport(item); setScreen('document'); }} className="min-w-0 flex-1 text-left"><p className="font-bold">{item.title}</p><p className="mt-1 text-xs text-slate-500">{item.type} · {new Date(item.createdAt).toLocaleString('ko-KR')}</p></button><button aria-label="보고서 휴지통으로 이동" onClick={() => moveReportToTrash(item.id)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700"><Trash2 size={16}/></button></div>) : <p className="rounded-xl bg-slate-50 p-8 text-center text-sm text-slate-500">보고서가 없습니다.</p>}</div></section>}
  {screen === 'trash' && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><h2 className="mr-auto text-lg font-black">보고서 휴지통</h2><button onClick={() => setScreen('reports')} className="rounded-xl border px-3 py-2 text-xs font-bold">보고서 목록</button></div><p className="mt-2 text-xs text-slate-500">삭제한 보고서는 30일 동안 보관됩니다.</p><div className="mt-4 space-y-2">{trashedReports.length ? trashedReports.map((item) => <div key={item.id} className="flex items-center gap-2 rounded-xl border p-3"><div className="min-w-0 flex-1"><p className="font-bold">{item.title}</p><p className="text-xs text-slate-500">삭제일 {new Date(item.deletedAt ?? '').toLocaleString('ko-KR')}</p></div><button onClick={() => restoreReport(item.id)} className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-xs font-bold"><RotateCcw size={14}/>복구</button><button onClick={() => removeReportPermanently(item.id)} className="rounded-lg bg-rose-600 px-3 py-2 text-xs font-bold text-white">삭제</button></div>) : <p className="rounded-xl bg-slate-50 p-8 text-center text-sm text-slate-500">휴지통이 비어 있습니다.</p>}</div></section>}
  {screen === 'document' && selectedReport && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-center gap-2"><h2 className="mr-auto text-lg font-black">{selectedReport.title}</h2><button onClick={downloadWord} className="inline-flex items-center gap-1 rounded-xl border px-3 py-2 text-xs font-bold"><Download size={14}/>Word 다운로드</button><button onClick={printPdf} className="inline-flex items-center gap-1 rounded-xl bg-slate-900 px-3 py-2 text-xs font-bold text-white"><Download size={14}/>PDF 저장</button></div><p className="mt-2 text-xs text-slate-500">PDF 저장은 브라우저 인쇄 창에서 ‘PDF로 저장’을 선택하세요.</p><iframe title={selectedReport.title} srcDoc={selectedReport.html} className="mt-4 h-[620px] w-full rounded-xl border bg-white" /></section>}
  {screen === 'work' && <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
    <section className="min-w-0">
      <ChatWorkspace
        key={view}
        title={meta[view].label}
        description={meta[view].description}
        headerActions={<div className="flex max-w-full shrink-0 items-center gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
          <span className="px-1.5 text-[10px] font-black text-slate-400">내부</span>
          <button type="button" onClick={() => setView('COLLABORATION')} className={`rounded-lg px-2.5 py-1.5 text-[11px] font-bold transition ${view === 'COLLABORATION' ? 'bg-slate-950 text-white shadow-sm' : 'text-slate-600 hover:bg-white'}`}>은행 협업</button>
          <button type="button" onClick={() => setView('AI_PRIVATE')} className={`rounded-lg px-2.5 py-1.5 text-[11px] font-bold transition ${view === 'AI_PRIVATE' ? 'bg-slate-950 text-white shadow-sm' : 'text-slate-600 hover:bg-white'}`}>AI 개인 작업 공간</button>
          <span className="mx-0.5 h-5 w-px bg-slate-300" aria-hidden="true" />
          <span className="px-1 text-[10px] font-black text-slate-400">외부</span>
          <button type="button" onClick={() => setView('CUSTOMER')} className={`rounded-lg px-2.5 py-1.5 text-[11px] font-bold transition ${view === 'CUSTOMER' ? 'bg-blue-600 text-white shadow-sm' : 'text-blue-700 hover:bg-white'}`}>고객 대화</button>
        </div>}
        messages={messages}
        placeholder={view === 'AI_PRIVATE' ? 'CaseCopilot에게 분석 또는 질문 초안을 요청하세요.' : '메시지를 입력하세요.'}
        currentUserId={currentUser.user_id}
        theme={view === 'CUSTOMER' ? 'light' : 'dark'}
        sending={sending}
        onSend={send}
        onUploadFile={uploadFile}
        attachmentView="bank"
        quickActions={view === 'AI_PRIVATE' ? getBankWorkCardActions() : []}
        onQuickAction={handleQuickAction}
        toolCards={view === 'AI_PRIVATE' ? <WorkCardRenderer card={activeCard} context={{ caseId, requestedBy: currentUser.display_name, currentCase, facts, onRefresh: load, onClose: () => setActiveCard(null), onOpenCard: openWorkCard }}/> : null}
        onShareMessage={view === 'AI_PRIVATE' ? shareAiMessage : undefined}
        sharingMessageId={sharingMessageId}
        draftStorageKey={`mvp-v2:draft:${caseId}:${view}`}
        heightClassName="h-[636px]"
        focusMessageId={focusMessageId}
      />
    </section>
    <aside className="grid h-[680px] min-h-0 grid-rows-[minmax(0,2fr)_minmax(0,3fr)] gap-4">
      <CaseLiveLog events={bundle?.recent_events ?? []} heightClassName="h-full" onMessageEvent={goToMessage} onWorkflowEvent={(event) => { if (event.event_type.startsWith('VERIFICATION_')) navigate(`/cases/${caseId}/verify`); }} emergencyMessageId={emergencyAlertMessage?.message_id}/>
      <section className="min-h-0 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><h2 className="text-sm font-black">우선 조치 및 위험요소</h2><div className="mt-3 space-y-2">{nextTasks.length ? <><p className="text-[11px] font-bold text-slate-500">지금 해야 할 일</p>{nextTasks.map((task, index) => <p key={task} className="rounded-xl bg-blue-50 p-3 text-xs leading-5 text-blue-900"><span className="mr-1 font-black">{index + 1}.</span>{task}</p>)}</> : <p className="rounded-xl bg-emerald-50 p-3 text-xs text-emerald-800">현재 확인이 필요한 우선 업무가 없습니다.</p>}<p className="pt-2 text-[11px] font-bold text-slate-500">확인된 위험요소</p>{risks.length ? risks.map((item) => <div key={item.verification_task_id} className="rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-900">{item.claim}</div>) : <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">확정된 위험요소가 없습니다.</p>}</div></section>
    </aside>
  </div>}
  {modal && <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/35 p-4"><section className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl"><div className="flex items-center justify-between"><h2 className="font-black">{modal === 'participants' ? 'Case 참여자' : modal === 'assignee' ? '메인 담당자 관리' : '사건 종료 확인'}</h2><button onClick={() => setModal(null)}><X size={18}/></button></div>{modal === 'participants' ? <div className="mt-4 space-y-2">{members.map((member) => { const state = presence.find((item) => item.user_id === member.user_id)?.presence; return <div key={member.user_id} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm"><div><p className="font-bold">{member.display_name}</p><p className="text-xs text-slate-500">{role[member.role]}</p></div><span className="rounded-full bg-emerald-50 px-2 py-1 text-[11px] font-bold text-emerald-700">{stateLabel(state)}</span></div>; })}</div> : modal === 'assignee' ? <><div className="mt-3 flex flex-wrap gap-2">{members.map((member) => <button key={member.user_id} onClick={() => setAssigneeDraft(member.display_name)} className="rounded-full border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-bold text-blue-800">{member.display_name} · {role[member.role]}</button>)}</div><input value={assigneeDraft} onChange={(event) => setAssigneeDraft(event.target.value)} placeholder="담당자 이름 입력" className="mt-4 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm"/><div className="mt-4 flex justify-end gap-2"><button onClick={() => setModal(null)} className="rounded-xl border px-4 py-2 text-sm font-bold">취소</button><button onClick={async () => { await mvpChatApi.setPrimaryAssignee(caseId, assigneeDraft.trim() || null); await load(); setModal(null); }} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white">저장</button></div></> : <><p className="mt-3 text-sm leading-6 text-slate-600">정말 사건을 종료하겠습니까? 최종 리포트를 작성한 뒤 보고서 목록으로 이동합니다.</p><div className="mt-5 flex justify-end gap-2"><button onClick={() => setModal(null)} className="rounded-xl border px-4 py-2 text-sm font-bold">아니요</button><button onClick={closeCase} className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-bold text-white">네, 종결합니다</button></div></>}</section></div>}</main></AppLayout>;
};
