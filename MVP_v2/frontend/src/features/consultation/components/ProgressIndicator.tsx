import React from 'react';

interface ProgressIndicatorProps {
  currentStep?: number;
  totalSteps?: number;
  steps?: string[];
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  currentStep = 0,
  totalSteps = 4,
  steps = ['상황 확인', '위험 확인', '조치 안내', '완료'],
}) => {
  return (
    <div className="w-full bg-white border-b border-gray-200 px-4 py-3 sticky top-16 z-30">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between gap-2">
          {steps.map((step, index) => (
            <React.Fragment key={step}>
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                    index <= currentStep
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {index + 1}
                </div>
                <div className="text-xs mt-1 text-gray-700 text-center">{step}</div>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`h-1 flex-1 mx-1 transition-colors ${
                    index < currentStep ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
                />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
};
