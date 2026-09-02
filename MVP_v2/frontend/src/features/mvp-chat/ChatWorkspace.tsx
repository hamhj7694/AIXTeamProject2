import React, { FormEvent, useEffect, useRef, useState } from 'react';
import { Bot, Paperclip, Send, ShieldCheck, UserRound } from 'lucide-react';
import type { MvpMessage } from '../../services/mvpChatApi';

interface ChatWorkspaceProps {
  title: string;
  description: string;
  channelLabel: string;
  messages: MvpMessage[];
  placeholder: string;
  sending?: boolean;
  onSend: (content: string) => Promise<void>;
}

const actorLabel: Record<MvpMessage['actor_type'], string> = {
  CUSTOMER: '고객', BANK_STAFF: '은행 담당자', CUSTOMER_AGENT: 'Customer Agent',
  BANK_AGENT: 'CaseCopilot', VERIFICATION: '기관 검증', SYSTEM: '시스템',
};

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({ title, description, channelLabel, messages, placeholder, sending = false, onSend }) => {
  const [draft, setDraft] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages.length]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sending) return;
    await onSend(content);
    setDraft('');
  };

  return <section className="flex min-h-[620px] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
    <header className="border-b border-slate-100 px-5 py-4">
      <div className="flex items-center justify-between gap-3"><div><h1 className="text-base font-black text-slate-900">{title}</h1><p className="mt-1 text-xs text-slate-500">{description}</p></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-600">{channelLabel}</span></div>
    </header>
    <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto bg-slate-50/70 p-4 sm:p-5" aria-live="polite">
      {messages.length === 0 && <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-6 text-center text-sm text-slate-500">아직 대화가 없습니다. 필요한 내용을 입력해 시작하세요.</div>}
      {messages.map((message) => {
        const mine = message.actor_type === 'CUSTOMER' || message.actor_type === 'BANK_STAFF';
        const agent = message.actor_type === 'CUSTOMER_AGENT' || message.actor_type === 'BANK_AGENT';
        return <article key={message.message_id} className={`flex gap-2.5 ${mine ? 'flex-row-reverse' : ''}`}>
          <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${mine ? 'bg-slate-800 text-white' : agent ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
            {agent ? <Bot size={16}/> : mine ? <UserRound size={16}/> : <ShieldCheck size={16}/>} 
          </div>
          <div className={`max-w-[82%] ${mine ? 'text-right' : ''}`}>
            <p className="mb-1 text-[11px] font-bold text-slate-500">{actorLabel[message.actor_type]}</p>
            <div className={`whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-left text-sm leading-6 ${mine ? 'rounded-tr-sm bg-slate-900 text-white' : 'rounded-tl-sm border border-slate-200 bg-white text-slate-700'}`}>{message.content}</div>
            <time className="mt-1 block text-[10px] text-slate-400">{new Date(message.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</time>
          </div>
        </article>;
      })}
    </div>
    <form onSubmit={submit} className="sticky bottom-0 border-t border-slate-200 bg-white p-3 sm:p-4">
      <div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-2 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100">
        <button type="button" className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-slate-400 hover:bg-white hover:text-blue-600" aria-label="첨부 기능은 준비 중"><Paperclip size={18}/></button>
        <textarea value={draft} onChange={(event) => setDraft(event.target.value)} rows={2} placeholder={placeholder} className="min-h-[44px] flex-1 resize-none border-0 bg-transparent px-1 py-2 text-sm outline-none" />
        <button type="submit" disabled={!draft.trim() || sending} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-blue-600 text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40" aria-label="메시지 전송"><Send size={17}/></button>
      </div>
      <p className="mt-2 px-1 text-[11px] text-slate-400">전송 후 저장된 Case 정보와 이벤트를 기준으로 화면이 갱신됩니다.</p>
    </form>
  </section>;
};
