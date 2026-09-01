import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Badge } from '../../../../components/ui/Badge';
import { Card } from '../../../../components/ui/Card';
import { cn } from '../../../../utils/helpers';
import {
  ManagerRoomProgressEvent,
  ManagerRoomProgressPhase,
} from '../../types';

interface ProgressTimelineProps {
  events: ManagerRoomProgressEvent[];
  embedded?: boolean;
  scrollable?: boolean;
}

type EventFilter = 'key' | 'all';

const phaseConfig: Array<{
  phase: ManagerRoomProgressPhase;
  title: string;
  description: string;
  phaseClassName: string;
  dotClassName: string;
}> = [
  {
    phase: 'past',
    title: '과거',
    description: '이미 완료된 사건 흐름',
    phaseClassName: 'bg-white',
    dotClassName: 'bg-slate-400',
  },
  {
    phase: 'current',
    title: '현재',
    description: '담당자가 처리하고 있는 단계',
    phaseClassName: 'bg-blue-50/70',
    dotClassName: 'bg-blue-600 ring-4 ring-blue-100',
  },
  {
    phase: 'next',
    title: '다음 단계',
    description: '현재 조사 이후 필요한 업무',
    phaseClassName: 'bg-slate-50/50',
    dotClassName: 'bg-blue-300',
  },
];

export const ProgressTimeline: React.FC<ProgressTimelineProps> = ({
  events,
  embedded = false,
  scrollable = false,
}) => {
  const [eventFilter, setEventFilter] = useState<EventFilter>('key');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const visibleEvents =
    eventFilter === 'key' ? events.filter((event) => event.isKey) : events;

  const content = (
    <section aria-labelledby="progress-timeline-title">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 id="progress-timeline-title" className="text-base font-extrabold text-slate-950">
                사건 Timeline
              </h2>
              <Badge variant="default">MVP Mock</Badge>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              현재 Case의 처리 흐름을 단계별로 확인합니다.
            </p>
          </div>

          <div
            className="inline-flex w-fit rounded-lg border border-slate-200 bg-slate-50 p-1"
            aria-label="Timeline 이벤트 필터"
          >
            {([
              ['key', '핵심 이벤트'],
              ['all', '전체 이벤트'],
            ] as const).map(([filter, label]) => {
              const active = eventFilter === filter;

              return (
                <button
                  key={filter}
                  type="button"
                  onClick={() => setEventFilter(filter)}
                  aria-pressed={active}
                  className={cn(
                    'rounded-md px-3 py-1.5 text-xs font-bold transition',
                    active
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-500 hover:bg-white hover:text-slate-900'
                  )}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        <div
          className={cn(
            scrollable &&
              'max-h-[420px] overflow-y-auto overscroll-contain [scrollbar-width:thin]'
          )}
        >
          {phaseConfig.map((phase) => {
            const phaseEvents = visibleEvents.filter(
              (event) => event.phase === phase.phase
            );

            return (
              <section
                key={phase.phase}
                aria-labelledby={`progress-phase-${phase.phase}`}
                className={cn(
                  'border-b border-slate-200 px-4 py-4 last:border-b-0 sm:px-5',
                  phase.phaseClassName
                )}
              >
                <div className="mb-2 flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <h3
                    id={`progress-phase-${phase.phase}`}
                    className={cn(
                      'text-sm font-extrabold',
                      phase.phase === 'current'
                        ? 'text-blue-800'
                        : 'text-slate-900'
                    )}
                  >
                    {phase.title}
                  </h3>
                  <span className="text-xs text-slate-500">
                    {phase.description}
                  </span>
                </div>

                <div className="divide-y divide-slate-200/80">
                  {phaseEvents.map((event) => {
                    const expanded = expandedEventId === event.id;

                    return (
                      <div
                        key={event.id}
                        className="py-3 first:pt-1 last:pb-1"
                      >
                        <div className="flex items-start gap-3">
                          <span
                            aria-hidden="true"
                            className={cn(
                              'mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full',
                              phase.dotClassName
                            )}
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
                              <div className="flex flex-wrap items-center gap-2">
                                <p
                                  className={cn(
                                    'text-sm text-slate-900',
                                    event.isKey ? 'font-extrabold' : 'font-semibold'
                                  )}
                                >
                                  {event.title}
                                </p>
                                <span className="text-[11px] font-semibold text-slate-400">
                                  {event.label}
                                </span>
                              </div>
                              <button
                                type="button"
                                onClick={() =>
                                  setExpandedEventId(expanded ? null : event.id)
                                }
                                aria-expanded={expanded}
                                className="inline-flex w-fit items-center gap-1 text-xs font-bold text-slate-500 hover:text-blue-700"
                              >
                                세부 보기
                                <ChevronDown
                                  size={14}
                                  className={cn(
                                    'transition-transform',
                                    expanded && 'rotate-180'
                                  )}
                                />
                              </button>
                            </div>
                            {expanded && (
                              <p className="mt-2 border-l-2 border-slate-200 pl-3 text-xs leading-5 text-slate-600">
                                {event.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>
    </section>
  );

  return embedded ? (
    content
  ) : (
    <Card className="rounded-xl border-slate-200 p-0 shadow-sm">
      {content}
    </Card>
  );
};
