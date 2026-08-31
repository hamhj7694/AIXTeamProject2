import React from 'react';
import { Card } from '../../../components/ui/Card';
import { ManagerRoomView } from '../types';

interface ManagerRoomViewPlaceholderProps {
  view: ManagerRoomView;
}

const placeholderContent: Record<
  ManagerRoomView,
  { title: string; description: string; nextStep: string }
> = {
  workspace: {
    title: 'AI 사건 워크스페이스',
    description: '현재 사건을 이해하고 AI 업무를 수행하는 영역입니다.',
    nextStep: '상세 기능은 STEP 2에서 구현합니다.',
  },
  progress: {
    title: '사건 진행 흐름',
    description: '과거 / 현재 / 다음 흐름을 확인하는 영역입니다.',
    nextStep: '상세 Timeline은 STEP 3에서 구현합니다.',
  },
  evidence: {
    title: '원본 Evidence',
    description: 'FDS 및 통화·STT 근거를 읽기 전용으로 확인하는 영역입니다.',
    nextStep: '상세 Evidence 기능은 STEP 4에서 구현합니다.',
  },
  customer: {
    title: '담당자용 고객 ROOM',
    description: '담당자가 고객과 확인하고 대화하기 위한 영역입니다.',
    nextStep: '메시지 기능은 STEP 5에서 구현합니다.',
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
      <p className="mt-2 text-sm font-medium text-slate-400">
        {content.nextStep}
      </p>
    </Card>
  );
};
