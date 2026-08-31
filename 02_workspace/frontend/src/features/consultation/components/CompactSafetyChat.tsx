import React, { useMemo, useState } from 'react';
import { Bot, Check, Send, UserRound } from 'lucide-react';

type ChatMessage = { id: number; role: 'ai' | 'counselor' | 'user'; text: string; choices?: string[] };

const initialMessages: ChatMessage[] = [
  { id: 1, role: 'ai', text: '안녕하세요. 현재 상황을 안전하게 확인하겠습니다.' },
  { id: 2, role: 'counselor', text: '이 통화에서 가장 확인하고 싶은 부분은 무엇인가요?' },
  { id: 3, role: 'ai', text: '먼저 송금 여부와 개인정보 전달 여부를 확인할게요.', choices: ['아직 송금하지 않았어요', '이미 송금했어요', '잘 모르겠어요'] },
];

const getReply = (text: string): ChatMessage => {
  if (text.includes('송금하지')) return { id: Date.now() + 1, role: 'counselor', text: '송금하지 않으셨다면 다행입니다. 상대방이 검찰·은행 등 기관을 사칭했는지 확인해볼까요?', choices: ['검찰이라고 했어요', '은행이라고 했어요', '잘 모르겠어요'] };
  if (text.includes('송금했')) return { id: Date.now() + 1, role: 'counselor', text: '피해가 발생했을 가능성이 있어요. 추가 송금은 멈추고 거래내역을 확인하겠습니다. 은행 담당자 확인이 필요합니다.' };
  if (text.includes('검찰')) return { id: Date.now() + 1, role: 'counselor', text: '검찰 사칭 부분이 의심되시는군요. 안전계좌로 이체하라는 요구도 있었나요?', choices: ['네, 요구했어요', '아니요', '기억나지 않아요'] };
  if (text.includes('은행')) return { id: Date.now() + 1, role: 'counselor', text: '은행 사칭 가능성을 확인하겠습니다. 대출이나 계좌 안전조치를 이유로 송금을 요구했나요?', choices: ['네', '아니요', '모르겠어요'] };
  if (text.includes('네') || text.includes('요구')) return { id: Date.now() + 1, role: 'counselor', text: '확인했습니다. 기관 사칭과 긴급 송금 요구가 함께 확인되어 추가 검증이 필요합니다. 개인정보나 인증번호도 전달했나요?', choices: ['전달했어요', '전달하지 않았어요', '모르겠어요'] };
  return { id: Date.now() + 1, role: 'counselor', text: `“${text}”라고 말씀하셨군요. 그 내용과 관련해 상대방이 요구한 행동이나 금액이 있었는지 알려주시겠어요?` };
};

const Avatar: React.FC<{ role: ChatMessage['role'] }> = ({ role }) => <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${role === 'ai' ? 'bg-blue-100 text-blue-700' : role === 'counselor' ? 'bg-violet-100 text-violet-700' : 'bg-slate-800 text-white'}`}>{role === 'ai' ? <Bot size={18}/> : <UserRound size={18}/>}</div>;

export const CompactSafetyChat: React.FC = () => {
  const [messages, setMessages] = useState(initialMessages); const [input, setInput] = useState(''); const [selected, setSelected] = useState<string[]>([]);
  const send = (value = input) => { const text = value.trim(); if (!text) return; setMessages(current => [...current, { id: Date.now(), role: 'user', text }, getReply(text)]); setInput(''); };
  const latestChoices = useMemo(() => messages[messages.length - 1]?.choices ?? [], [messages]);
  const toggleChoice = (choice: string) => setSelected(current => current.includes(choice) ? current.filter(item => item !== choice) : [...current, choice]);
  return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-base font-extrabold">Customer Agent Chat</h2><p className="mt-1 text-xs text-slate-400">AI와 상담사가 Case 정보를 함께 확인합니다.</p></div><span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600"><span className="h-2 w-2 rounded-full bg-emerald-500"/> 연결됨</span></div><div className="h-[440px] space-y-4 overflow-y-auto rounded-xl bg-slate-50 p-4">{messages.map(message => <div key={message.id} className={`flex gap-2.5 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}><Avatar role={message.role}/><div className={`max-w-[82%] ${message.role === 'user' ? 'text-right' : ''}`}><p className="mb-1 text-[11px] font-extrabold text-slate-500">{message.role === 'ai' ? 'AI 안내' : message.role === 'counselor' ? '상담사' : '나'}</p><div className={`rounded-2xl px-3.5 py-3 text-sm leading-6 ${message.role === 'user' ? 'rounded-tr-sm bg-blue-600 text-white' : 'rounded-tl-sm bg-white text-slate-700 shadow-sm'}`}>{message.text}</div></div></div>)}</div>{latestChoices.length > 0 && <div className="mt-4"><p className="mb-2 text-xs font-bold text-slate-500">빠른 응답</p><div className="flex flex-wrap gap-2">{latestChoices.map(choice => <label key={choice} className={`inline-flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs font-bold ${selected.includes(choice) ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 bg-white text-slate-600'}`}><input type="checkbox" checked={selected.includes(choice)} onChange={() => toggleChoice(choice)} className="h-3.5 w-3.5 accent-blue-600"/>{choice}</label>)}<button onClick={() => selected.forEach(choice => send(choice))} disabled={!selected.length} className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white disabled:opacity-40"><Check size={13} className="mr-1 inline"/> 선택 전송</button></div></div>}<div className="mt-4 flex gap-2"><input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') send(); }} placeholder="메시지를 입력하세요..." className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500"/><button onClick={() => send()} disabled={!input.trim()} aria-label="메시지 전송" className="rounded-xl bg-blue-600 px-4 text-white disabled:opacity-40"><Send size={17}/></button></div></section>;
};
