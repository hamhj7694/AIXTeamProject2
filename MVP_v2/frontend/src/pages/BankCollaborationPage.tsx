import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, CircleDot, UsersRound } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CaseLiveLog } from '../features/mvp-chat/CaseLiveLog';
import { ChatWorkspace } from '../features/mvp-chat/ChatWorkspace';
import { mvpChatApi, type CaseBundleV2, type CaseMember, type CasePresence, type MessageChannel, type MvpMessage } from '../services/mvpChatApi';

const currentUser = { user_id: 'mvp-v2-current-user', display_name: '현재 사용자', role: 'CHAT_OPERATOR' as const };
const channelMeta: Record<MessageChannel, { label: string; description: string }> = {
  TEAM: { label: '팀 협업', description: '사람끼리 협의하는 내부 채널입니다. AI는 @CaseCopilot 호출에만 응답합니다.' },
  CUSTOMER: { label: '고객 대화', description: '고객에게 실제로 전달되는 메시지 채널입니다.' },
  AI_INTERNAL: { label: 'AI 업무 대화', description: 'CaseCopilot의 내부 분석과 질문 초안을 확인합니다.' },
};

export const BankCollaborationPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const [channel, setChannel] = useState<MessageChannel>('TEAM');
  const [bundle, setBundle] = useState<CaseBundleV2 | null>(null);
  const [messages, setMessages] = useState<MvpMessage[]>([]);
  const [members, setMembers] = useState<CaseMember[]>([]);
  const [presence, setPresence] = useState<CasePresence[]>([]);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async (targetChannel = channel) => {
    const [nextBundle, nextMessages, nextMembers, nextPresence] = await Promise.all([
      mvpChatApi.getBundle(caseId, 'bank'), mvpChatApi.listMessages(caseId, targetChannel), mvpChatApi.listMembers(caseId), mvpChatApi.listPresence(caseId),
    ]);
    setBundle(nextBundle); setMessages(nextMessages); setMembers(nextMembers); setPresence(nextPresence);
  }, [caseId, channel]);
  useEffect(() => { mvpChatApi.upsertMember(caseId, currentUser).then(() => load()).catch((reason) => setError(reason instanceof Error ? reason.message : 'Case 협업 Room을 불러오지 못했습니다.')); }, [caseId, load]);
  useEffect(() => { load().catch(() => undefined); }, [channel, load]);
  useEffect(() => { const beat = () => mvpChatApi.heartbeat(caseId, { ...currentUser, presence: 'VIEWING', channel }).then(() => load()).catch(() => undefined); void beat(); const timer = window.setInterval(beat, 20000); return () => window.clearInterval(timer); }, [caseId, channel, load]);
  const send = async (content: string) => { setSending(true); try {
    if (channel === 'AI_INTERNAL') { const response = await mvpChatApi.invokeCopilot(caseId, content, 'AI_INTERNAL'); setMessages((items) => [...items, response]); return; }
    const isCopilotMention = channel === 'TEAM' && /@CaseCopilot\b/i.test(content);
    const created = await mvpChatApi.createMessage(caseId, { actor_type: 'BANK_STAFF', content, channel, audience: channel === 'CUSTOMER' ? 'CUSTOMER' : 'BANK_INTERNAL', mentions: isCopilotMention ? ['CaseCopilot'] : [] });
    setMessages((items) => [...items, created]);
    if (isCopilotMention) { const response = await mvpChatApi.invokeCopilot(caseId, content, 'TEAM'); setChannel('AI_INTERNAL'); setMessages([response]); }
  } finally { setSending(false); } };
  const currentCase = bundle?.case ?? {};
  const activeViewers = useMemo(() => presence.filter((item) => item.presence !== 'AWAY').length, [presence]);
  const roleLabel: Record<CaseMember['role'], string> = { CASE_OWNER: 'Case 담당', CHAT_OPERATOR: '채팅 담당', REVIEWER: '검토', VIEWER: '보고 중' };

  return <AppLayout><main className="mx-auto max-w-[1440px] py-6 lg:ml-64"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><Link to={`/cases/${caseId}`} className="inline-flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16}/> Case로 돌아가기</Link><span className="text-[11px] font-bold text-slate-400">BANK CASE COLLABORATION ROOM</span></div>
    <section className="mb-4 rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3"><div><div className="flex items-center gap-2"><h1 className="text-lg font-black">{String(currentCase.case_id ?? caseId)}</h1><span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-bold text-blue-700">{String(currentCase.status ?? 'TRIAGE')}</span></div><p className="mt-1 text-xs text-slate-500">{String(currentCase.initial_brief ?? 'Case 정보를 불러오는 중입니다.')}</p></div><span className="rounded-lg bg-rose-50 px-3 py-2 text-xs font-bold text-rose-700">긴급 조치 검토</span></div>
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3"><UsersRound size={16} className="text-blue-600"/>{members.length === 0 ? <span className="text-xs text-slate-400">참여자 없음</span> : members.slice(0, 3).map((member) => <span key={member.user_id} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-600"><span className="grid h-4 w-4 place-items-center rounded-full bg-slate-700 text-[9px] text-white">{member.display_name.slice(0, 1)}</span>{roleLabel[member.role]} {member.display_name}</span>)}<span className="ml-1 inline-flex items-center gap-1 text-xs font-semibold text-emerald-700"><CircleDot size={13}/> 보고 중 {activeViewers}명</span></div>
    </section>
    {error && <p className="mb-4 rounded-xl bg-rose-50 p-3 text-sm font-semibold text-rose-700">{error}</p>}
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_330px]"><section><div className="mb-3 flex flex-wrap gap-2">{(Object.keys(channelMeta) as MessageChannel[]).map((key) => <button key={key} onClick={() => setChannel(key)} className={`rounded-xl px-3 py-2 text-xs font-bold ${channel === key ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`}>{channelMeta[key].label}</button>)}</div><ChatWorkspace title={channelMeta[channel].label} description={channelMeta[channel].description} channelLabel={channel} messages={messages} placeholder={channel === 'TEAM' ? '팀 메시지 또는 @CaseCopilot 요청을 입력하세요.' : channel === 'CUSTOMER' ? '고객에게 전달할 메시지를 입력하세요.' : 'CaseCopilot에게 내부 업무를 요청하세요.'} sending={sending} onSend={send}/></section><CaseLiveLog events={bundle?.recent_events ?? []}/></div>
  </main></AppLayout>;
};
