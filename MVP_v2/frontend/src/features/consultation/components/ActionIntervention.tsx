import React from 'react';
import { Button } from '../../../components/ui/Button';

interface ActionInterventionProps {
  type?: 'stop_money_transfer' | 'stop_personal_info' | 'already_damaged';
  onStopAction?: () => void;
  onContinue?: () => void;
}

export const ActionIntervention: React.FC<ActionInterventionProps> = ({
  type = 'stop_money_transfer',
  onStopAction,
  onContinue,
}) => {
  const getContent = () => {
    switch (type) {
      case 'stop_money_transfer':
        return {
          title: '잠시만요.',
          subtitle: '지금은 송금을 잠시 멈춰주세요.',
          description:
            '지금까지 확인한 상황을 먼저 확인한 뒤\n안전한 방법으로 처리하는 것이 좋습니다.',
          primaryButtonText: '송금 잠시 멈추기',
        };
      case 'stop_personal_info':
        return {
          title: '잠시만요.',
          subtitle: '개인정보 공개를 멈춰주세요.',
          description:
            '비밀번호나 인증번호는 금융기관도 요청하지 않습니다.\n현재 상황을 확인해주세요.',
          primaryButtonText: '정보 공개 멈추기',
        };
      case 'already_damaged':
        return {
          title: '괜찮아요.',
          subtitle: '지금부터 함께 해결해봅시다.',
          description:
            '이미 피해가 발생했다면, 지금부터 추가 피해를 막기 위한 조치를 안내해드릴게요.',
          primaryButtonText: '조치 안내 받기',
        };
      default:
        return {
          title: '확인이 필요합니다.',
          subtitle: '',
          description: '현재 상황을 다시 한번 확인해주세요.',
          primaryButtonText: '확인했습니다',
        };
    }
  };

  const content = getContent();

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 animate-slideUp">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">{content.title}</h2>
        {content.subtitle && (
          <h3 className="text-lg font-semibold text-red-600 mb-4">{content.subtitle}</h3>
        )}
        <p className="text-base text-gray-700 mb-6 whitespace-pre-wrap leading-relaxed">
          {content.description}
        </p>

        <div className="flex flex-col gap-3">
          <Button
            onClick={onStopAction}
            variant={type === 'already_damaged' ? 'success' : 'danger'}
            size="lg"
            fullWidth
          >
            {content.primaryButtonText}
          </Button>
          {onContinue && (
            <Button
              onClick={onContinue}
              variant="secondary"
              size="md"
              fullWidth
            >
              계속 확인하기
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
