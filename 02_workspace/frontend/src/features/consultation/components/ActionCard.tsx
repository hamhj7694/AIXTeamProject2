import React from 'react';
import { Card } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';

interface ActionCardProps {
  title?: string;
  description?: string;
  actions: string[];
  primaryButtonText?: string;
  secondaryButtonText?: string;
  onPrimaryAction?: () => void;
  onSecondaryAction?: () => void;
}

export const ActionCard: React.FC<ActionCardProps> = ({
  title = '지금 해야 할 행동',
  description,
  actions,
  primaryButtonText = '완료',
  secondaryButtonText,
  onPrimaryAction,
  onSecondaryAction,
}) => {
  return (
    <Card className="bg-green-50 border border-green-200 mb-4 message-enter">
      <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
      {description && <p className="text-sm text-gray-700 mb-3">{description}</p>}
      
      <ol className="space-y-2 mb-4 text-sm text-gray-800">
        {actions.map((action, index) => (
          <li key={index} className="flex gap-2">
            <span className="font-bold text-green-600 min-w-6">{index + 1}.</span>
            <span>{action}</span>
          </li>
        ))}
      </ol>

      <div className="flex flex-col gap-2">
        {onPrimaryAction && (
          <Button
            onClick={onPrimaryAction}
            variant="success"
            size="md"
            fullWidth
          >
            {primaryButtonText}
          </Button>
        )}
        {onSecondaryAction && (
          <Button
            onClick={onSecondaryAction}
            variant="secondary"
            size="md"
            fullWidth
          >
            {secondaryButtonText}
          </Button>
        )}
      </div>
    </Card>
  );
};
