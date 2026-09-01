import React from 'react';
import { FileClock } from 'lucide-react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { cn } from '../../../../utils/helpers';
import { ManagerRoomCase, ManagerRoomFinalReport } from '../../types';

interface FinalReportProps {
  caseInfo: ManagerRoomCase;
  report: ManagerRoomFinalReport | null;
}

interface DocumentSectionProps {
  number: number;
  title: string;
  introduction?: string;
  children: React.ReactNode;
}

const DocumentSection: React.FC<DocumentSectionProps> = ({
  number,
  title,
  introduction,
  children,
}) => (
  <section className="border-t border-slate-200 py-7 sm:py-8">
    <h3 className="text-base font-black tracking-tight text-slate-950 sm:text-lg">
      {number}. {title}
    </h3>
    {introduction && (
      <p className="mt-3 text-sm leading-7 text-slate-600">{introduction}</p>
    )}
    <div className="mt-4">{children}</div>
  </section>
);

interface ReportBulletListProps {
  items: string[];
  accent?: 'default' | 'danger';
  emptyText?: string;
}

const ReportBulletList: React.FC<ReportBulletListProps> = ({
  items,
  accent = 'default',
  emptyText = '현재 기록된 내용이 없습니다.',
}) => {
  if (!items.length) {
    return <p className="text-sm leading-7 text-slate-500">{emptyText}</p>;
  }

  return (
    <ul className="space-y-2.5 text-sm leading-7 text-slate-700">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="flex items-start gap-3">
          <span
            aria-hidden="true"
            className={cn(
              'mt-[11px] h-1.5 w-1.5 shrink-0 rounded-full',
              accent === 'danger' ? 'bg-rose-500' : 'bg-slate-400'
            )}
          />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
};

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

  const completedChecklistItems = report.checklistItems
    .filter((item) => item.completed)
    .map((item) => `${item.label} · 확인 완료`);
  const pendingChecklistItems = report.checklistItems
    .filter((item) => !item.completed)
    .map((item) => `${item.label} · 추가 확인 필요`);

  return (
    <article aria-labelledby="final-report-title" className="mx-auto max-w-5xl">
      <Card className="overflow-hidden rounded-xl border-slate-200 bg-white p-0 shadow-sm">
        <header className="border-b border-slate-300 px-5 py-7 sm:px-10 sm:py-10">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-700">
                Case report
              </p>
              <h2
                id="final-report-title"
                className="mt-2 text-2xl font-black tracking-tight text-slate-950 sm:text-3xl"
              >
                최종 사건 보고서
              </h2>
              <p className="mt-2 text-sm font-bold text-slate-500">
                CASE #{report.caseId}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="danger">위험도 {report.risk}</Badge>
              <Badge variant="success">{report.status}</Badge>
              <Badge variant="default">MVP Mock</Badge>
            </div>
          </div>

          <dl className="mt-7 grid gap-x-8 gap-y-4 border-t border-slate-200 pt-6 sm:grid-cols-3">
            <div>
              <dt className="text-xs font-bold text-slate-500">담당자</dt>
              <dd className="mt-1 text-sm font-extrabold text-slate-900">
                {report.assignee}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-bold text-slate-500">최초 종료</dt>
              <dd className="mt-1 text-sm font-extrabold text-slate-900">
                {report.closedAt}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-bold text-slate-500">
                리포트 최종 갱신
              </dt>
              <dd className="mt-1 text-sm font-extrabold text-slate-900">
                {report.reportUpdatedAt}
              </dd>
            </div>
          </dl>
        </header>

        <div className="px-5 sm:px-10">
          <DocumentSection number={1} title="사건 개요">
            <p className="text-sm leading-8 text-slate-700">{report.summary}</p>
          </DocumentSection>

          <DocumentSection
            number={2}
            title="주요 확인 결과"
            introduction="조사 체크리스트와 현재 기록을 기준으로 확인 상태를 정리했습니다."
          >
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <h4 className="text-sm font-extrabold text-slate-900">
                  확인 완료 항목
                </h4>
                <div className="mt-2">
                  <ReportBulletList
                    items={completedChecklistItems}
                    emptyText="현재 체크리스트에서 확인 완료로 기록된 항목이 없습니다."
                  />
                </div>
              </div>
              <div>
                <h4 className="text-sm font-extrabold text-slate-900">
                  판단 참고 사항
                </h4>
                <div className="mt-2">
                  <ReportBulletList items={report.counterEvidence} />
                </div>
              </div>
            </div>
          </DocumentSection>

          <DocumentSection
            number={3}
            title="주요 위험 정황"
            introduction="조사 과정에서 다음과 같은 위험 정황이 확인되었습니다."
          >
            <ReportBulletList items={report.riskEvidence} accent="danger" />
          </DocumentSection>

          <DocumentSection number={4} title="조사 및 고객 확인 결과">
            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-extrabold text-slate-900">
                  고객 상담 기록
                </h4>
                <div className="mt-2">
                  <ReportBulletList items={report.customerFindings} />
                </div>
              </div>
              <div>
                <h4 className="text-sm font-extrabold text-slate-900">
                  담당자 내부 메모
                </h4>
                <div className="mt-2">
                  <ReportBulletList
                    items={report.internalMemos.map((memo) => memo.content)}
                    emptyText="현재 작성된 내부 메모가 없습니다."
                  />
                </div>
              </div>
            </div>
          </DocumentSection>

          <DocumentSection number={5} title="담당자 처리 결과">
            <ReportBulletList items={report.resolution} />
          </DocumentSection>

          <DocumentSection number={6} title="미확인 및 후속 확인 사항">
            <ReportBulletList
              items={[...report.unknowns, ...pendingChecklistItems]}
              emptyText="현재 기록 기준 추가로 확인이 필요한 항목이 없습니다."
            />
          </DocumentSection>

          <DocumentSection number={7} title="근거 출처">
            <ReportBulletList items={report.evidenceSources} />
          </DocumentSection>
        </div>

        <footer className="border-t border-slate-300 bg-slate-50 px-5 py-5 text-xs leading-6 text-slate-500 sm:px-10">
          본 보고서는 사건 처리 과정에서 수집된 정보와 담당자의 확인 내용을
          문서화한 업무 기록입니다. 최종 판단과 조치의 주체는 담당자입니다.
        </footer>
      </Card>
    </article>
  );
};
