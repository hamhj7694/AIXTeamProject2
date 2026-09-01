import React from 'react';
import { Card } from '../../../components/ui/Card';
import { ManagerRoomView } from '../types';

interface ManagerRoomViewPlaceholderProps {
  view: ManagerRoomView;
}

const placeholderContent: Record<
  ManagerRoomView,
  { title: string; description: string }
> = {
  workspace: {
    title: 'AI 사건 워크스페이스',
    description: '현재 사건을 이해하고 AI 업무를 수행하는 영역입니다.',
  },
  progress: {
    title: '사건 진행 흐름',
    description: '과거 / 현재 / 다음 흐름을 확인하는 영역입니다.',
  },
  evidence: {
    title: '근거 확인',
    description: 'FDS 및 통화·STT 근거를 읽기 전용으로 확인하는 영역입니다.',
  },
};

export const ManagerRoomViewPlaceholder: React.FC<
  ManagerRoomViewPlaceholderProps
> = ({ view }) => {
  const content = placeholderContent[view];

  return (
    <Card
      variant="elevated"
      className="flex min-h-[360px] flex-col items-center justify-center border border-slate-200 px-6 py-16 text-center"
    >
      <p className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">
        Manager ROOM
      </p>
      <h2 className="text-2xl font-bold text-slate-950">{content.title}</h2>
      <p className="mt-4 max-w-xl text-base text-slate-600">
        {content.description}
      </p>
    </Card>
  );
};
