import React from 'react';
import { RiskSignal } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';

interface RiskSignalCardProps {
  signals: RiskSignal[];
}

export const RiskSignalCard: React.FC<RiskSignalCardProps> = ({ signals }) => {
  if (!signals || signals.length === 0) {
    return null;
  }

  const highRiskCount = signals.filter((s) => s.severity === 'high').length;

  const variantMap = {
    high: 'danger' as const,
    medium: 'warning' as const,
    low: 'default' as const,
  };

  return (
    <Card className="bg-red-50 border border-red-200 mb-4 message-enter">
      <div className="mb-3">
        <h3 className="font-semibold text-gray-900 mb-2">확인된 위험 신호</h3>
        {highRiskCount > 0 && (
          <Badge variant="danger" size="sm" className="mb-2">
            높은 위험도 {highRiskCount}개 감지
          </Badge>
        )}
      </div>
      <ul className="space-y-2 text-sm">
        {signals.map((signal) => (
          <li key={signal.id} className="flex gap-2 items-start">
            <span className="text-red-600 font-bold">•</span>
            <div>
              <span className="text-gray-800">{signal.signal}</span>
              {signal.explanation && (
                <p className="text-xs text-gray-600 mt-0.5">{signal.explanation}</p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
};
