import React from 'react';
import { UserRound } from 'lucide-react';
import { Badge } from '../../../components/ui/Badge';
import { managerRoomAssigneesMock } from '../data/managerRoomMock';

export const ManagerAssigneeOverview: React.FC = () => {
  return (
    <section
      aria-labelledby="manager-assignee-title"
      className="-mt-px border border-slate-200 bg-slate-50/60 px-4 py-3 sm:px-5"
    >
      <div className="grid gap-3 md:grid-cols-[130px_minmax(0,1fr)] md:items-center">
        <div className="flex flex-wrap items-center gap-2">
          <h2
            id="manager-assignee-title"
            className="text-sm font-extrabold text-slate-900"
          >
            담당자 현황
          </h2>
          <Badge variant="default">MVP Mock</Badge>
        </div>

        <div className="grid gap-2 sm:grid-cols-2 sm:gap-0 sm:divide-x sm:divide-slate-200">
          {managerRoomAssigneesMock.map((assignee) => (
            <div
              key={assignee.role}
              className="flex min-w-0 items-center gap-3 rounded-lg bg-white px-3 py-2 sm:rounded-none sm:bg-transparent sm:first:pl-0 sm:last:pr-0 sm:last:pl-4"
            >
              <span
                aria-hidden="true"
                className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-blue-50 text-blue-600"
              >
                <UserRound size={16} />
              </span>
              <div className="min-w-0">
                <p className="text-[11px] font-semibold text-slate-500">
                  {assignee.role}
                </p>
                <div className="mt-0.5 flex flex-wrap items-center gap-2">
                  <p className="text-sm font-extrabold text-slate-900">
                    {assignee.name}
                  </p>
                  <span className="rounded-md bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700">
                    {assignee.workStatus}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
