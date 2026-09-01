import React, { useEffect, useRef, useState } from 'react';
import { Mic, Phone, PhoneOff, Volume2, X } from 'lucide-react';

export type VoiceCallRole = 'customer' | 'bank';

interface VoiceCallPopupProps {
  open: boolean;
  role: VoiceCallRole;
  onClose: () => void;
  onCallStarted?: () => void;
  onRecordingReady?: (url: string) => void;
}

const roleCopy = {
  customer: { title: '은행 담당자와 통화', subtitle: '안전한 상담을 시작합니다', person: '은행 안전상담 담당자' },
  bank: { title: '고객과 통화', subtitle: 'Case 담당자 연결 중', person: '고객' },
};

export const VoiceCallPopup: React.FC<VoiceCallPopupProps> = ({ open, role, onClose, onCallStarted, onRecordingReady }) => {
  const [calling, setCalling] = useState(false);
  const [muted, setMuted] = useState(false);
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const dragOffset = useRef({ x: 0, y: 0 });
  const recorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunks = useRef<Blob[]>([]);
  const copy = roleCopy[role];

  useEffect(() => {
    if (!open) {
      setCalling(false);
      setMuted(false);
      setPosition(null);
    }
  }, [open]);

  const handleDragStart = (event: React.PointerEvent<HTMLDivElement>) => {
    const popup = popupRef.current;
    if (!popup) return;
    const rect = popup.getBoundingClientRect();
    setPosition((current) => current ?? { x: rect.left, y: rect.top });
    dragOffset.current = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handleDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
    const width = popupRef.current?.offsetWidth ?? 320;
    const height = popupRef.current?.offsetHeight ?? 260;
    const x = Math.min(Math.max(8, event.clientX - dragOffset.current.x), window.innerWidth - width - 8);
    const y = Math.min(Math.max(8, event.clientY - dragOffset.current.y), window.innerHeight - height - 8);
    setPosition({ x, y });
  };

  const startCall = async () => {
    setCalling(true);
    onCallStarted?.();
    if (!navigator.mediaDevices?.getUserMedia || !('MediaRecorder' in window)) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordedChunks.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => { if (event.data.size > 0) recordedChunks.current.push(event.data); };
      recorder.start();
      recorderRef.current = recorder;
    } catch {
      // 마이크 권한이 없어도 통화 UI는 계속 사용할 수 있습니다.
    }
  };

  const finishCall = () => {
    const recorder = recorderRef.current;
    if (!recorder) { onClose(); return; }
    recorder.onstop = () => {
      const blob = new Blob(recordedChunks.current, { type: recorder.mimeType || 'audio/webm' });
      onRecordingReady?.(URL.createObjectURL(blob));
      recorder.stream.getTracks().forEach((track) => track.stop());
      recorderRef.current = null;
      onClose();
    };
    recorder.stop();
  };

  if (!open) return null;

  return (
    <div ref={popupRef} style={position ? { left: position.x, top: position.y } : undefined} className={`fixed z-50 w-[calc(100vw-2rem)] max-w-xs overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-slate-900/20 ${position ? '' : 'left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2'}`}>
      <div onPointerDown={handleDragStart} onPointerMove={handleDrag} className="flex cursor-move touch-none items-center justify-between border-b border-slate-100 bg-slate-900 px-4 py-3 text-white">
        <div className="flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-full ${calling ? 'animate-pulse bg-emerald-400' : 'bg-amber-400'}`} /><span className="text-xs font-bold">{calling ? '통화 중' : '음성 통화'}</span></div>
        <button type="button" aria-label="통화 팝업 닫기" onPointerDown={(event) => event.stopPropagation()} onClick={calling ? finishCall : onClose} className="rounded-md p-1 text-slate-300 transition hover:bg-white/10 hover:text-white"><X size={16} /></button>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-3"><div className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-blue-50 text-blue-600"><Phone size={21} /></div><div className="min-w-0"><p className="truncate text-sm font-extrabold text-slate-900">{copy.person}</p><p className="mt-0.5 text-xs text-slate-500">{calling ? '연결되었습니다' : copy.subtitle}</p></div></div>
        <p className="mt-4 rounded-xl bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">{calling ? '통화 내용을 Case Timeline에 기록할 수 있습니다.' : copy.title}</p>
        <div className="mt-4 flex items-center justify-center gap-3">
          {calling && <button type="button" aria-label={muted ? '마이크 켜기' : '마이크 끄기'} onClick={() => setMuted((value) => !value)} className={`grid h-10 w-10 place-items-center rounded-full ${muted ? 'bg-rose-100 text-rose-600' : 'bg-slate-100 text-slate-700'}`}><Mic size={17} /></button>}
          <button type="button" aria-label={calling ? '통화 종료' : '통화 요청'} onClick={calling ? finishCall : startCall} className={`grid h-11 w-11 place-items-center rounded-full text-white shadow-sm transition hover:scale-105 ${calling ? 'bg-rose-600 hover:bg-rose-700' : 'bg-emerald-600 hover:bg-emerald-700'}`}>{calling ? <PhoneOff size={19} /> : <Phone size={19} />}</button>
          {calling && <button type="button" aria-label="스피커 설정" className="grid h-10 w-10 place-items-center rounded-full bg-slate-100 text-slate-700"><Volume2 size={17} /></button>}
        </div>
        {!calling && <p className="mt-3 text-center text-[11px] text-slate-400">초록색 버튼을 눌러 통화를 시작하세요</p>}
      </div>
    </div>
  );
};
