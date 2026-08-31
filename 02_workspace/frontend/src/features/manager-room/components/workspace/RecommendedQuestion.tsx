import React from 'react';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { Card } from '../../../../components/ui/Card';

interface RecommendedQuestionProps {
  question: string;
  onOpenCustomerView: () => void;
}

export const RecommendedQuestion: React.FC<RecommendedQuestionProps> = ({
  question,
  onOpenCustomerView,
}) => {
  return (
    <Card className="rounded-xl border-blue-100 bg-blue-50/30 p-5 shadow-sm">
      <section
        aria-labelledby="recommended-question-title"
        className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
      >
        <div className="max-w-4xl">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="recommended-question-title" className="text-base font-extrabold text-slate-950">
              AI 추천 확인 질문
            </h2>
            <Badge variant="default">MVP Mock</Badge>
          </div>
          <p className="mt-2.5 text-sm font-bold leading-6 text-slate-800">
            “{question}”
          </p>
          <p className="mt-1.5 text-xs leading-5 text-slate-500">
            AI가 고객에게 자동 전송하지 않습니다. 담당자가 확인한 뒤 고객 ROOM에서 수정·전송합니다.
          </p>
        </div>

        <Button
          type="button"
          variant="primary"
          onClick={onOpenCustomerView}
          className="shrink-0"
        >
          고객 ROOM에서 확인 →
        </Button>
      </section>
    </Card>
  );
};
