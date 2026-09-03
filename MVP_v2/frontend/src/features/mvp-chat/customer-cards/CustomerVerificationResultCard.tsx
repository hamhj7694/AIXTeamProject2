import React from 'react';
import { BadgeCheck } from 'lucide-react';
import type { CustomerVerificationResult } from './types';

export const CustomerVerificationResultCard: React.FC<{ result: CustomerVerificationResult }> = ({ result }) => (
  <article className="rounded-2xl border border-blue-200 bg-blue-50 p-4 shadow-sm">
    <div className="flex items-center gap-2 text-blue-800"><BadgeCheck size={17}/><p className="text-xs font-black">공식 확인 결과</p></div>
    <p className="mt-2 text-sm font-black text-slate-900">{result.target}</p>
    <p className="mt-2 text-xs leading-5 text-slate-700">{result.result_summary}</p>
    <p className="mt-3 rounded-xl bg-white p-3 text-[11px] leading-5 text-slate-600">은행 담당자가 고객 공개를 승인한 내용입니다. 추가 확인이 필요한 경우 상담 채팅에서 질문해 주세요.</p>
  </article>
);
