import React from 'react';
import { SituationInfo } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';

interface SituationCardProps {
  situations: SituationInfo[];
  onEdit?: () => void;
}

export const SituationCard: React.FC<SituationCardProps> = ({ situations, onEdit }) => {
  if (!situations || situations.length === 0) {
    return null;
  }

  return (
    <Card className="bg-blue-50 border border-blue-200 mb-4 message-enter">
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="font-semibold text-gray-900">현재 상황</h3>
        {onEdit && (
          <Button variant="ghost" size="sm" onClick={onEdit} className="text-xs">
            내용 수정
          </Button>
        )}
      </div>
      <ul className="space-y-2 text-sm text-gray-800">
        {situations.map((info, index) => (
          <li key={info.id} className="flex gap-2">
            <span className="text-blue-600 font-semibold">•</span>
            <span>{info.description}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
};
