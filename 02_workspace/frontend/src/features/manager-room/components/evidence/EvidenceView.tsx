import React from 'react';
import { FileText, ShieldAlert } from 'lucide-react';
import { Card } from '../../../../components/ui/Card';

interface EvidenceViewProps {
  evidence: string[];
}

export const EvidenceView: React.FC<EvidenceViewProps> = ({ evidence }) => (
  <section aria-labelledby="evidence-view-title" className="space-y-4">
    <div>
      <h2 id="evidence-view-title" className="text-lg font-black text-slate-950">근거 확인</h2>
      <p className="mt-1 text-sm leading-6 text-slate-600">현재 Case의 실제 AI 진단 결과에서 추출된 근거입니다. 외부 FDS·STT 원문은 아직 연동되지 않았습니다.</p>
    </div>
    <Card className="overflow-hidden border-slate-200 p-0 shadow-sm">
      <div className="border-b border-slate-200 p-4 sm:p-5"><div className="flex items-center gap-2"><ShieldAlert size={18} className="text-rose-600"/><h3 className="text-base font-extrabold text-slate-900">진단 근거</h3></div></div>
      <div className="space-y-3 p-4 sm:p-5">{evidence.length ? evidence.map((item, index) => <article key={`${item}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 p-4"><div className="flex items-center gap-2 text-xs font-bold text-blue-700"><FileText size={14}/> Evidence {String(index + 1).padStart(2, '0')}</div><p className="mt-2 text-sm leading-6 text-slate-700">{item}</p></article>) : <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">저장된 진단 근거가 없습니다.</p>}</div>
    </Card>
  </section>
);
