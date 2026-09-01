import React from 'react';
import { Choice } from '../../../types';
import { Button } from '../../../components/ui/Button';

interface QuickReplyProps {
  choices: Choice[];
  onChoose: (choice: Choice) => void;
  isLoading?: boolean;
}

export const QuickReply: React.FC<QuickReplyProps> = ({ choices, onChoose, isLoading = false }) => {
  return (
    <div className="flex w-full flex-col items-center gap-2">
      {choices.map((choice) => (
        <Button
          key={choice.id}
          onClick={() => onChoose(choice)}
          disabled={isLoading}
          variant="secondary"
          size="sm"
          className="w-[92%] max-w-md text-left h-auto py-2.5 px-3 whitespace-normal justify-start text-sm leading-relaxed"
        >
          {choice.label}
        </Button>
      ))}
    </div>
  );
};
