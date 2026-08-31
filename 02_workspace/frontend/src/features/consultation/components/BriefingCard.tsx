import React from 'react';
import { Card } from '../../../components/ui/Card';

interface BriefingCardProps {
  items: string[];
  title?: string;
}

export const BriefingCard: React.FC<BriefingCardProps> = ({
  items,
  title = '지금까지 확인한 내용',
}) => {
  if (!items || items.length === 0) {
    return null;
  }

  return (
    <Card className="bg-amber-50 border border-amber-200 mb-4 message-enter">
      <h3 className="font-semibold text-gray-900 mb-3">{title}</h3>
      <ul className="space-y-2 text-sm text-gray-800">
        {items.map((item, index) => (
          <li key={index} className="flex gap-2">
            <span className="text-amber-600 font-semibold">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
};
