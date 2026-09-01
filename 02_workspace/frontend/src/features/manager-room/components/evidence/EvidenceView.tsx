import React, { useState } from 'react';
import { FileText, ShieldAlert } from 'lucide-react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { cn } from '../../../../utils/helpers';
import {
  managerRoomFdsMock,
  managerRoomSttMock,
} from '../../data/managerRoomMock';
import { ManagerRoomEvidenceSource } from '../../types';

const evidenceSources: Array<{
  id: ManagerRoomEvidenceSource;
  label: string;
  description: string;
}> = [
  {
    id: 'fds',
    label: 'FDS 화면 보기',
    description: '금융거래 위험 신호',
  },
  {
    id: 'stt',
    label: '통화·STT 보기',
    description: '상담 근거 발췌',
  },
];

const FdsDetail: React.FC = () => {
  return (
    <article aria-labelledby="fds-detail-title">
      <div className="border-b border-slate-200 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 id="fds-detail-title" className="text-base font-extrabold text-rose-900">
            FDS 위험 신호
          </h3>
          <Badge variant="default">MVP Mock</Badge>
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          금융거래 시스템에서 담당자 검토가 필요한 신호가 감지된 내용입니다.
        </p>
      </div>

      <div className="space-y-5 p-4 sm:p-5">
        <div className="rounded-lg border border-rose-100 bg-rose-50/50 p-4">
          <p className="text-sm font-extrabold text-rose-900">
            {managerRoomFdsMock.signalStatus}
          </p>
          <p className="mt-2 text-sm leading-6 text-rose-800">
            {managerRoomFdsMock.summary}
          </p>
        </div>

        <dl className="divide-y divide-slate-100 rounded-lg border border-slate-200">
          <div className="grid gap-1 p-3 sm:grid-cols-[140px_minmax(0,1fr)] sm:gap-4 sm:p-4">
            <dt className="text-xs font-bold text-slate-500">신호 상태</dt>
            <dd className="text-sm font-extrabold text-rose-700">
              {managerRoomFdsMock.signalStatus}
            </dd>
          </div>
          <div className="grid gap-1 p-3 sm:grid-cols-[140px_minmax(0,1fr)] sm:gap-4 sm:p-4">
            <dt className="text-xs font-bold text-slate-500">담당자 상태</dt>
            <dd className="text-sm font-semibold text-amber-700">
              {managerRoomFdsMock.managerStatus}
            </dd>
          </div>
          <div className="grid gap-2 p-3 sm:grid-cols-[140px_minmax(0,1fr)] sm:gap-4 sm:p-4">
            <dt className="text-xs font-bold text-slate-500">상세 정보</dt>
            <dd>
              <p className="text-sm font-semibold text-slate-700">정보 미제공</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {managerRoomFdsMock.unavailableDetails.map((detail) => (
                  <span
                    key={detail}
                    className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-500"
                  >
                    {detail}
                  </span>
                ))}
              </div>
            </dd>
          </div>
        </dl>

        <section aria-labelledby="fds-confirmation-title">
          <h4 id="fds-confirmation-title" className="text-sm font-extrabold text-slate-900">
            담당자 확인 의미
          </h4>
          <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-600">
            {managerRoomFdsMock.confirmationPoints.map((point) => (
              <li key={point} className="flex gap-2">
                <span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </article>
  );
};

const SttDetail: React.FC = () => {
  return (
    <article aria-labelledby="stt-detail-title">
      <div className="border-b border-slate-200 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 id="stt-detail-title" className="text-base font-extrabold text-slate-950">
            통화·STT
          </h3>
          <Badge variant="warning">{managerRoomSttMock.sourceLabel}</Badge>
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          통화 맥락에서 확인할 위험 정황을 읽기 전용으로 정리한 영역입니다.
        </p>
      </div>

      <div className="space-y-5 p-4 sm:p-5">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
          <strong className="font-extrabold">자료 안내:</strong>{' '}
          {managerRoomSttMock.notice}
        </div>

        <section aria-labelledby="stt-excerpt-title">
          <h4 id="stt-excerpt-title" className="text-sm font-extrabold text-slate-900">
            Mock 발췌 내용
          </h4>
          <div className="mt-3 space-y-3">
            {managerRoomSttMock.excerpts.map((excerpt) => (
              <div key={excerpt.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-bold text-blue-700">{excerpt.speaker}</p>
                <p className="mt-1.5 text-sm leading-6 text-slate-700">
                  {excerpt.content}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section aria-labelledby="stt-confirmation-title">
          <h4 id="stt-confirmation-title" className="text-sm font-extrabold text-slate-900">
            확인 가능한 정황
          </h4>
          <ul className="mt-2 grid gap-2 sm:grid-cols-2">
            {managerRoomSttMock.confirmationPoints.map((point) => (
              <li
                key={point}
                className="rounded-md border border-slate-100 bg-white px-3 py-2 text-sm leading-5 text-slate-600"
              >
                {point}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </article>
  );
};

export const EvidenceView: React.FC = () => {
  const [selectedSource, setSelectedSource] =
    useState<ManagerRoomEvidenceSource>('fds');

  return (
    <section aria-labelledby="evidence-view-title" className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="evidence-view-title" className="text-lg font-black text-slate-950">
            근거 확인
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            사건 판단에 참고할 입력 자료를 소스별로 확인합니다. 모든 내용은 읽기 전용입니다.
          </p>
        </div>
        <Badge variant="default">MVP Mock</Badge>
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
        <Card className="border-slate-200 p-2 shadow-sm">
          <p className="px-2 pb-2 pt-1 text-xs font-bold text-slate-500">
            확인할 근거
          </p>
          <div
            role="tablist"
            aria-label="근거 소스 선택"
            className="grid grid-cols-2 gap-2 lg:block lg:space-y-2"
          >
            {evidenceSources.map((source) => {
              const active = selectedSource === source.id;
              const Icon = source.id === 'fds' ? ShieldAlert : FileText;

              return (
                <button
                  key={source.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  aria-controls={`${source.id}-evidence-panel`}
                  onClick={() => setSelectedSource(source.id)}
                  className={cn(
                    'flex w-full items-start gap-2 rounded-lg border px-3 py-3 text-left transition-colors',
                    active
                      ? 'border-blue-200 bg-blue-50 text-blue-900'
                      : 'border-transparent text-slate-600 hover:border-slate-200 hover:bg-slate-50'
                  )}
                >
                  <Icon size={17} className="mt-0.5 shrink-0" />
                  <span className="min-w-0">
                    <span className="block text-sm font-extrabold">{source.label}</span>
                    <span className="mt-0.5 hidden text-xs leading-5 text-slate-500 sm:block">
                      {source.description}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </Card>

        <Card className="overflow-hidden border-slate-200 p-0 shadow-sm">
          <div
            id={`${selectedSource}-evidence-panel`}
            role="tabpanel"
            aria-live="polite"
          >
            {selectedSource === 'fds' ? <FdsDetail /> : <SttDetail />}
          </div>
        </Card>
      </div>
    </section>
  );
};
