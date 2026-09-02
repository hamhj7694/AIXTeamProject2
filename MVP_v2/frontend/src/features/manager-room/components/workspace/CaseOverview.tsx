import React from 'react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { ManagerRoomWorkspaceMock } from '../../types';

interface CaseOverviewProps {
  workspace: ManagerRoomWorkspaceMock;
}

const summarySections: Array<{
  key: 'riskEvidence' | 'counterEvidence' | 'unknowns';
  title: string;
  sectionClassName: string;
  titleClassName: string;
  bulletClassName: string;
}> = [
  {
    key: 'riskEvidence',
    title: '위험 근거',
    sectionClassName: 'bg-rose-50/40',
    titleClassName: 'text-rose-800',
    bulletClassName: 'bg-rose-500',
  },
  {
    key: 'counterEvidence',
    title: '반대 근거',
    sectionClassName: 'bg-emerald-50/40',
    titleClassName: 'text-emerald-800',
    bulletClassName: 'bg-emerald-500',
  },
  {
    key: 'unknowns',
    title: '미확인 사항',
    sectionClassName: 'bg-amber-50/40',
    titleClassName: 'text-amber-800',
    bulletClassName: 'bg-amber-500',
  },
];

export const CaseOverview: React.FC<CaseOverviewProps> = ({ workspace }) => {
  return (
    <section aria-labelledby="case-brief-title" className="space-y-3">
      <Card className="rounded-xl border-blue-100 bg-blue-50/40 p-4 shadow-sm">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <h3 id="case-brief-title" className="text-base font-extrabold text-slate-950">
            사건 Brief
          </h3>
          <Badge variant="default">General API</Badge>
        </div>
        <p className="max-w-5xl text-sm leading-6 text-slate-700">{workspace.brief}</p>
        <p className="mt-3 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500">
          AI 정리는 조사 보조 정보입니다. 근거 자료 확인과 최종 판단은 담당자가 수행합니다.
        </p>
      </Card>

      <Card className="overflow-hidden rounded-xl border-slate-200 p-0 shadow-sm">
        <div className="flex flex-wrap items-center gap-2 px-4 py-3.5">
          <h3 className="text-base font-extrabold text-slate-950">근거 분석</h3>
          <Badge variant="default">General API</Badge>
        </div>

        <div className="divide-y divide-slate-200 border-t border-slate-200">
          {summarySections.map((section) => (
            <section
              key={section.key}
              aria-labelledby={`case-overview-${section.key}`}
              className={`px-4 py-3.5 ${section.sectionClassName}`}
            >
              <h4
                id={`case-overview-${section.key}`}
                className={`text-sm font-extrabold ${section.titleClassName}`}
              >
                {section.title}
              </h4>
              <ul
                aria-label={`${section.title} 내용 목록`}
                className="mt-2 max-h-[110px] space-y-1.5 overflow-y-auto overscroll-contain pr-2 text-sm leading-5 text-slate-700 [scrollbar-width:thin]"
              >
                {workspace[section.key].map((item) => (
                  <li key={item} className="flex gap-2">
                    <span
                      aria-hidden="true"
                      className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${section.bulletClassName}`}
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </Card>
    </section>
  );
};
