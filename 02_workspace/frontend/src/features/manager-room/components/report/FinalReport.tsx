import React from 'react';
import { ClipboardCheck, FileClock } from 'lucide-react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { ManagerRoomCase, ManagerRoomFinalReport } from '../../types';

interface FinalReportProps {
  caseInfo: ManagerRoomCase;
  report: ManagerRoomFinalReport | null;
}

interface ReportListProps {
  title: string;
  items: string[];
  className: string;
  titleClassName: string;
  bulletClassName: string;
}

const ReportList: React.FC<ReportListProps> = ({
  title,
  items,
  className,
  titleClassName,
  bulletClassName,
}) => (
  <section className={`rounded-xl border p-4 sm:p-5 ${className}`}>
    <h3 className={`text-sm font-extrabold ${titleClassName}`}>{title}</h3>
    <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="flex gap-2.5">
          <span
            aria-hidden="true"
            className={`mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full ${bulletClassName}`}
          />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  </section>
);

export const FinalReport: React.FC<FinalReportProps> = ({ caseInfo, report }) => {
  if (!report) {
    return (
      <section aria-labelledby="final-report-title" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="final-report-title" className="text-lg font-black text-slate-950">
            최종 리포트
          </h2>
          <Badge variant="warning">{caseInfo.status}</Badge>
        </div>

        <Card className="flex min-h-[360px] flex-col items-center justify-center rounded-xl border-slate-200 px-6 py-14 text-center shadow-sm">
          <span className="grid h-14 w-14 place-items-center rounded-full bg-slate-100 text-slate-500">
            <FileClock size={26} />
          </span>
          <h3 className="mt-4 text-xl font-black text-slate-950">
            사건 조사가 완료되지 않았습니다.
          </h3>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">
            사건 종료 후 현재까지의 조사 내용과 확인 결과를 기반으로 최종 리포트가 생성됩니다.
          </p>
        </Card>
      </section>
    );
  }

  const basicInformation = [
    ['Case ID', report.caseId],
    ['위험 수준', report.risk],
    ['사건 상태', report.status],
    ['담당자', report.assignee],
    ['최초 종료 시각', report.closedAt],
    ['리포트 최종 갱신', report.reportUpdatedAt],
  ] as const;

  return (
    <article aria-labelledby="final-report-title" className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="final-report-title" className="text-lg font-black text-slate-950">
              최종 리포트
            </h2>
            <Badge variant="success">생성 완료</Badge>
          </div>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            마지막 갱신 시점까지 기록된 조사 및 확인 내용을 정리했습니다.
          </p>
        </div>
        <Badge variant="default">MVP Mock</Badge>
      </div>

      <Card className="overflow-hidden rounded-xl border-slate-200 p-0 shadow-sm">
        <section className="border-b border-slate-200 bg-slate-50/70 p-4 sm:p-5">
          <div className="flex items-center gap-2">
            <ClipboardCheck size={18} className="text-blue-600" />
            <h3 className="text-sm font-extrabold text-slate-950">사건 기본 정보</h3>
          </div>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {basicInformation.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5">
                <dt className="text-[11px] font-bold text-slate-500">{label}</dt>
                <dd className="mt-1 break-words text-sm font-extrabold text-slate-900">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        <div className="space-y-4 p-4 sm:p-5">
          <section className="rounded-xl border border-blue-100 bg-blue-50/40 p-4 sm:p-5">
            <h3 className="text-sm font-extrabold text-blue-900">사건 요약</h3>
            <p className="mt-3 text-sm leading-7 text-slate-700">{report.summary}</p>
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <ReportList
              title="주요 위험 근거"
              items={report.riskEvidence}
              className="border-rose-100 bg-rose-50/40"
              titleClassName="text-rose-800"
              bulletClassName="bg-rose-500"
            />
            <ReportList
              title="반대 근거"
              items={report.counterEvidence}
              className="border-emerald-100 bg-emerald-50/40"
              titleClassName="text-emerald-800"
              bulletClassName="bg-emerald-500"
            />
          </div>

          <ReportList
            title="고객 확인 결과"
            items={report.customerFindings}
            className="border-blue-100 bg-blue-50/30"
            titleClassName="text-blue-900"
            bulletClassName="bg-blue-500"
          />
          <ReportList
            title="미확인 사항"
            items={report.unknowns}
            className="border-amber-100 bg-amber-50/40"
            titleClassName="text-amber-800"
            bulletClassName="bg-amber-500"
          />
          <ReportList
            title="조사 체크리스트"
            items={report.checklistItems.map(
              (item) => `${item.completed ? '확인 완료' : '미확인'} · ${item.label}`
            )}
            className="border-blue-100 bg-blue-50/30"
            titleClassName="text-blue-900"
            bulletClassName="bg-blue-500"
          />
          <ReportList
            title="내부 메모"
            items={
              report.internalMemos.length
                ? report.internalMemos.map((memo) => memo.content)
                : ['작성된 내부 메모가 없습니다.']
            }
            className="border-slate-200 bg-white"
            titleClassName="text-slate-900"
            bulletClassName="bg-slate-400"
          />
          <ReportList
            title="담당자 처리 결과"
            items={report.resolution}
            className="border-slate-200 bg-slate-50"
            titleClassName="text-slate-900"
            bulletClassName="bg-slate-500"
          />
        </div>

        <p className="border-t border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-500 sm:px-5">
          본 리포트는 사건 처리 과정에서 수집된 정보와 담당자의 확인 내용을 정리한 업무 기록입니다.
        </p>
      </Card>
    </article>
  );
};
