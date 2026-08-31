import React, { useMemo, useState } from 'react';
import { Bot, Check, ImagePlus, Paperclip, Send, UserRound, X } from 'lucide-react';

type ChatRole = 'ai' | 'counselor' | 'user';
export type QuestionKey = 'transfer' | 'amount' | 'personal' | 'personalDegree' | 'link' | 'impersonation' | 'call' | 'done';
interface ChatMessage { id: number; role: ChatRole; text: string; choices?: string[]; attachments?: { name: string; preview?: string; isImage: boolean }[]; }
interface Question { key: QuestionKey; prompt: string; choices: string[]; }
interface CompactSafetyChatProps { onResponse?: (question: QuestionKey, answer: string) => void; }

const questions: Record<Exclude<QuestionKey, 'done'>, Question> = {
  transfer: { key: 'transfer', prompt: '먼저 송금 여부를 확인할게요. 현재 송금을 진행하셨나요?', choices: ['아니요, 송금하지 않았어요', '네, 보냈습니다', '일부만 보냈습니다', '잘 모르겠습니다'] },
  amount: { key: 'amount', prompt: '송금하셨다면 얼마를 보내셨나요?', choices: ['100만원 미만', '100만원 이상 500만원 미만', '500만원 이상', '잘 모르겠습니다'] },
  personal: { key: 'personal', prompt: '상대방에게 개인정보를 전달하셨나요?', choices: ['제공하지 않았습니다', '이름만 제공했습니다', '개인정보를 제공했습니다', '잘 모르겠습니다'] },
  personalDegree: { key: 'personalDegree', prompt: '개인정보를 제공했다면 어느 정도인가요?', choices: ['이름·연락처만 제공했습니다', '주민번호·계좌번호를 제공했습니다', '인증번호·비밀번호를 제공했습니다', '잘 모르겠습니다'] },
  link: { key: 'link', prompt: '상대방이 보낸 링크나 앱을 확인했나요?', choices: ['눌렀습니다', '누르지 않았습니다', '앱을 설치했습니다', '잘 모르겠습니다'] },
  impersonation: { key: 'impersonation', prompt: '상대방이 기관이나 담당자를 사칭했나요?', choices: ['네, 기관을 사칭했습니다', '아니요', '잘 모르겠습니다'] },
  call: { key: 'call', prompt: '상대방과 전화 통화를 했나요?', choices: ['통화했습니다', '통화하지 않았습니다', '잘 모르겠습니다'] },
};

const firstMessages: ChatMessage[] = [
  { id: 1, role: 'ai', text: '안녕하세요. 현재 상황을 안전하게 확인하겠습니다.' },
  { id: 2, role: 'ai', text: '이 통화에서 가장 확인하고 싶은 부분은 무엇인가요?' },
  { id: 3, role: 'ai', text: questions.transfer.prompt, choices: questions.transfer.choices },
];

const getNextQuestion = (key: QuestionKey, answer: string): Question | undefined => {
  if (key === 'transfer') return answer.startsWith('아니요') ? questions.personal : questions.amount;
  if (key === 'amount') return questions.personal;
  if (key === 'personal') return answer.startsWith('제공하지') ? questions.link : questions.personalDegree;
  if (key === 'personalDegree') return questions.link;
  if (key === 'link') return questions.impersonation;
  if (key === 'impersonation') return questions.call;
  return undefined;
};

const getAcknowledgement = (key: QuestionKey, answer: string) => {
  if (key === 'transfer' && answer.startsWith('아니요')) return '송금하지 않은 것으로 기록했습니다. 개인정보를 전달했는지 확인할게요.';
  if (key === 'transfer') return `송금 여부를 “${answer}”로 기록했습니다. 송금 금액을 확인할게요.`;
  if (key === 'amount') return `송금 금액을 “${answer}”로 기록했습니다. 개인정보 제공 여부를 확인할게요.`;
  if (key === 'personal' && answer.startsWith('제공하지')) return '개인정보를 제공하지 않은 것으로 기록했습니다. 링크나 앱을 확인했는지 살펴볼게요.';
  if (key === 'personal') return '개인정보 제공 사실을 기록했습니다. 어떤 정보가 노출됐는지 확인할게요.';
  if (key === 'personalDegree') return `노출 범위를 “${answer}”로 기록했습니다. 링크나 앱을 확인했는지 살펴볼게요.`;
  if (key === 'link') return `링크 또는 앱 관련 답변을 “${answer}”로 기록했습니다. 상대방의 신원을 확인할게요.`;
  if (key === 'impersonation') return `기관 사칭 여부를 “${answer}”로 기록했습니다. 마지막으로 통화 여부를 확인할게요.`;
  if (key === 'call') return `통화 여부를 “${answer}”로 기록했습니다. 지금까지의 답변을 정리할게요.`;
  return `답변을 “${answer}”로 기록했습니다.`;
};

const requiresCounselor = (key: QuestionKey, answer: string) => (
  (key === 'transfer' && (answer.includes('보냈') || answer.includes('일부'))) ||
  (key === 'personalDegree' && (answer.includes('주민') || answer.includes('인증') || answer.includes('비밀번호'))) ||
  (key === 'link' && (answer.includes('눌렀') || answer.includes('설치'))) ||
  (key === 'impersonation' && answer.startsWith('네'))
);

const Avatar: React.FC<{ role: ChatRole }> = ({ role }) => (
  <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${role === 'ai' ? 'bg-blue-100 text-blue-600' : role === 'user' ? 'bg-slate-200 text-slate-600' : 'bg-violet-100 text-violet-600'}`}>
    {role === 'ai' ? <Bot size={18} /> : <UserRound size={18} />}
  </div>
);

export const CompactSafetyChat: React.FC<CompactSafetyChatProps> = ({ onResponse }) => {
  const [messages, setMessages] = useState<ChatMessage[]>(firstMessages);
  const [input, setInput] = useState('');
  const [currentQuestion, setCurrentQuestion] = useState<QuestionKey>('transfer');
  const [attachments, setAttachments] = useState<{ name: string; preview?: string; isImage: boolean }[]>([]);
  const latestChoices = useMemo(() => messages[messages.length - 1]?.choices ?? [], [messages]);

  const respond = (answer: string) => {
    const trimmed = answer.trim();
    if ((!trimmed && attachments.length === 0) || currentQuestion === 'done') return;
    onResponse?.(currentQuestion, trimmed);
    const next = getNextQuestion(currentQuestion, trimmed);
    const response: ChatMessage[] = [{ id: Date.now(), role: 'user', text: trimmed || '첨부 파일을 보냈습니다.', attachments }];
    if (requiresCounselor(currentQuestion, trimmed)) response.push({ id: Date.now() + 1, role: 'counselor', text: '위험 신호가 감지되었습니다. 필요하면 상담사 확인을 요청할 수 있습니다. AI가 우선 확인을 계속하겠습니다.' });
    response.push({ id: Date.now() + 2, role: 'ai', text: getAcknowledgement(currentQuestion, trimmed) });
    response.push(next ? { id: Date.now() + 3, role: 'ai', text: next.prompt, choices: next.choices } : { id: Date.now() + 3, role: 'ai', text: '필요한 답변을 모두 확인했습니다. 추가로 설명할 내용이 있으면 아래 입력창에 남겨주세요.' });
    setMessages((current) => [...current, ...response]);
    setCurrentQuestion(next?.key ?? 'done');
    setInput('');
    setAttachments([]);
  };

  const addAttachments = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    const nextFiles = files.map((file) => ({
      name: file.name,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      isImage: file.type.startsWith('image/'),
    }));
    setAttachments((current) => [...current, ...nextFiles]);
    event.target.value = '';
  };

  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5" aria-label="Customer Agent Chat">
    <div className="mb-4 flex items-start justify-between gap-3"><div><h2 className="text-base font-extrabold text-slate-900">Customer Agent Chat</h2><p className="mt-1 text-xs text-slate-400">AI가 답변에 맞춰 다음 질문을 이어갑니다.</p></div><span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-600"><span className="h-2 w-2 rounded-full bg-emerald-500" /> 연결됨</span></div>
    <div className="h-[520px] overflow-y-auto rounded-2xl bg-slate-50 p-3 sm:p-4"><div className="space-y-4">{messages.map((message) => <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}><Avatar role={message.role}/><div className={`max-w-[82%] ${message.role === 'user' ? 'text-right' : ''}`}><p className="mb-1 text-[11px] font-bold text-slate-500">{message.role === 'ai' ? 'AI 안내' : message.role === 'user' ? '내 답변' : '상담사'}</p><div className={`rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${message.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white text-slate-700'}`}><span className="whitespace-pre-wrap">{message.text}</span>{message.attachments && message.attachments.length > 0 && <div className="mt-2 space-y-2">{message.attachments.map((file) => <div key={file.name} className="flex items-center gap-2 rounded-lg bg-black/10 p-2 text-left text-xs"><span className="shrink-0">{file.isImage && file.preview ? <img src={file.preview} alt={file.name} className="h-12 w-12 rounded object-cover"/> : <Paperclip size={14}/>}</span><span className="truncate">{file.name}</span></div>)}</div>}</div></div></div>)}</div>{latestChoices.length > 0 && <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50/60 p-3"><p className="mb-2 text-xs font-extrabold text-blue-700">현재 상황에 해당하는 답변을 선택해주세요</p><div className="space-y-2">{latestChoices.map((choice) => <label key={choice} className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700 transition hover:border-blue-400 hover:bg-blue-50"><input type="checkbox" aria-label={choice} className="h-4 w-4 accent-blue-600" onChange={() => respond(choice)}/><span>{choice}</span><Check size={15} className="ml-auto text-blue-500"/></label>)}</div></div>}</div>
    <form className="mt-3" onSubmit={(event) => { event.preventDefault(); respond(input); }}>
      {attachments.length > 0 && <div className="mb-2 flex flex-wrap gap-2">{attachments.map((file, index) => <span key={`${file.name}-${index}`} className="inline-flex max-w-full items-center gap-1 rounded-lg bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700"><span className="max-w-40 truncate">{file.name}</span><button type="button" aria-label={`${file.name} 첨부 취소`} onClick={() => setAttachments((current) => current.filter((_, fileIndex) => fileIndex !== index))}><X size={13}/></button></span>)}</div>}
      <div className="flex gap-2"><div className="flex shrink-0 items-center gap-1 rounded-xl border border-slate-200 bg-white px-1"><label className="grid h-10 w-10 cursor-pointer place-items-center rounded-lg text-slate-500 hover:bg-slate-100" title="파일 첨부"><Paperclip size={17}/><input type="file" multiple className="sr-only" onChange={addAttachments}/></label><label className="grid h-10 w-10 cursor-pointer place-items-center rounded-lg text-slate-500 hover:bg-slate-100" title="사진 첨부"><ImagePlus size={17}/><input type="file" accept="image/*" multiple className="sr-only" onChange={addAttachments}/></label></div><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="메시지를 입력하세요..." className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none placeholder:text-slate-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-100"/><button type="submit" aria-label="메시지 전송" className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-blue-600 text-white hover:bg-blue-700"><Send size={18}/></button></div>
    </form>
  </section>;
};
