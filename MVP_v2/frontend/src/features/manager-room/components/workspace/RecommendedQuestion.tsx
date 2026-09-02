import React from 'react';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { Card } from '../../../../components/ui/Card';

interface RecommendedQuestionProps {
  question: string;
  onUseInCustomerConsultation: () => void;
}

export const RecommendedQuestion: React.FC<RecommendedQuestionProps> = ({
  question,
  onUseInCustomerConsultation,
}) => {
  return (
    <Card className="rounded-xl border-blue-100 bg-blue-50/30 p-4 shadow-sm">
      <section aria-labelledby="recommended-question-title">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="recommended-question-title" className="text-base font-extrabold text-slate-950">
              AI 추천 확인 질문
            </h2>
            <Badge variant="default">AI Agent 연동 대기</Badge>
          </div>
          <p className="mt-2.5 text-sm font-bold leading-6 text-slate-800">
            “{question}”
          </p>
          <p className="mt-1.5 text-xs leading-5 text-slate-500">
            AI가 고객에게 자동 전송하지 않습니다. 담당자의 확인이 필요합니다.
          </p>
          <Button
            type="button"
            size="sm"
            onClick={onUseInCustomerConsultation}
            className="mt-3 w-full"
          >
            고객 상담에서 사용
          </Button>
        </div>
      </section>
    </Card>
  );
};
