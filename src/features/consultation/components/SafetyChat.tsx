import React, { useEffect, useRef, useState } from 'react';
import { useConsultation } from '../hooks/useConsultation';
import { handleConsultationFlow, getNextMessage } from '../consultationFlow';
import { ChatMessage } from './ChatMessage';
import { QuickReply } from './QuickReply';
import { ProgressIndicator } from './ProgressIndicator';
import { SituationCard } from './SituationCard';
import { RiskSignalCard } from './RiskSignalCard';
import { ActionIntervention } from './ActionIntervention';
import { ChatInput } from './ChatInput';
import { Choice, Message } from '../../../types';

/**
 * 위험도 계산
 */
const classifyRiskLevel = (signals: any[]): 'critical' | 'high' | 'medium' | 'low' => {
  const criticalCount = signals.filter(s => s.severity === 'high').length;
  if (criticalCount >= 3) return 'critical';
  if (criticalCount >= 2) return 'high';
  if (criticalCount >= 1) return 'medium';
  return 'low';
};

/**
 * 위험도별 색상
 */
const getRiskColor = (level: string) => {
  switch(level) {
    case 'critical': return 'border-red-300 bg-red-50';
    case 'high': return 'border-orange-300 bg-orange-50';
    case 'medium': return 'border-yellow-300 bg-yellow-50';
    default: return 'border-green-300 bg-green-50';
  }
};

/**
 * 위험도별 조치사항
 */
const getActionsByRiskLevel = (level: string): string[] => {
  const actions = {
    critical: [
      '⛔ 지금 바로 모든 행동을 멈추세요',
      '📞 은행에 즉시 전화 (24시간)',
      '🚨 경찰 신고: 112',
      '📋 금융감시원 신고: 1332',
      '💳 계좌 정지 요청',
      '📱 의심 앱 즉시 삭제',
    ],
    high: [
      '🛑 행동하지 말고 먼저 확인하세요',
      '☎️ 은행/기관 공식 번호로 확인',
      '👨‍👩‍👧 가족/친구와 상의하세요',
      '📞 의심스러우면 경찰에 신고 (112)',
      '💡 안전 안내 탭 확인',
    ],
    medium: [
      '⚠️ 신중하게 대응하세요',
      '✅ 공식 기관에 확인',
      '📌 개인정보 공개 금지',
      '📱 의심 앱 설치 금지',
    ],
    low: [
      'ℹ️ 일단 안전한 상황입니다',
      '🔍 의심스러우면 신고하세요',
      '💡 항상 신중함이 최고의 방어입니다',
    ],
  };
  return actions[level] || [];
};

export const SafetyChat: React.FC = () => {
  const store = useConsultation();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [currentStep, setCurrentStep] = useState('situation_check');
  const [showBriefing, setShowBriefing] = useState(false);
  const [showRiskAssessment, setShowRiskAssessment] = useState(false);
  const [showActionPlan, setShowActionPlan] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    store.initializeSession();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [store.messages]);

  // 단계별 표시 상태 업데이트
  useEffect(() => {
    if (currentStep === 'briefing') {
      setShowBriefing(true);
      setShowRiskAssessment(false);
      setShowActionPlan(false);
    } else if (currentStep === 'risk_assessment') {
      setShowRiskAssessment(true);
      setShowActionPlan(false);
    } else if (currentStep === 'action_plan') {
      setShowActionPlan(true);
    }
  }, [currentStep]);

  const handleChoiceSelect = async (choice: Choice) => {
    store.setLoading(true);
    
    store.addUserMessage(choice.label);
    
    await new Promise(resolve => setTimeout(resolve, 500));

    const result = getNextMessage(currentStep, choice.value);
    
    if (result) {
      await new Promise(resolve => setTimeout(resolve, 300));
      
      store.addMessage(result.message);
      
      if (result.riskSignal) {
        store.addRiskSignal(result.riskSignal);
      }
      
      if (result.situationInfo) {
        store.addSituationInfo(result.situationInfo);
      }
      
      setCurrentStep(result.nextStep);
      
      if (result.shouldShowIntervention && result.interventionType) {
        store.showIntervention(result.interventionType as any);
      }
    }
    
    store.setLoading(false);
  };

  const handleTextInput = (message: string) => {
    store.addUserMessage(message);
  };

  const getLastMessage = (): Message | null => {
    for (let i = store.messages.length - 1; i >= 0; i--) {
      if (store.messages[i].role === 'assistant') {
        return store.messages[i];
      }
    }
    return null;
  };

  const lastMessage = getLastMessage();
  const riskLevel = classifyRiskLevel(store.session?.detectedSignals ?? []);
  const riskActions = getActionsByRiskLevel(riskLevel);
  const currentProgress = ['situation_check', 'caller_identity', 'bank_reason'].includes(currentStep) ? 0
    : ['bank_action', 'transfer_timeline'].includes(currentStep) ? 1
    : ['transfer_readiness', 'briefing'].includes(currentStep) ? 2
    : 3;

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] bg-white">
      {/* 진행도 표시 */}
      <ProgressIndicator currentStep={currentProgress} totalSteps={4} />

      {/* 채팅 영역 */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-4xl mx-auto w-full">
        {/* 메시지 목록 */}
        <div className="space-y-4">
          {store.messages.map((message) => (
            <div key={message.id}>
              <ChatMessage message={message} />
            </div>
          ))}
        </div>

        {/* 상황 정보 */}
        {showBriefing && store.session?.situationInfo && store.session.situationInfo.length > 0 && (
          <div className="mt-6 p-4 border-2 border-blue-300 bg-blue-50 rounded-lg">
            <h3 className="font-bold text-blue-900 mb-3">📋 상황 정리</h3>
            {store.session.situationInfo.map((sit, idx) => (
              <div key={idx} className="text-blue-800 mb-2">
                • {sit.description}
              </div>
            ))}
          </div>
        )}

        {/* 위험 신호 표시 */}
        {showRiskAssessment && store.session?.detectedSignals && store.session.detectedSignals.length > 0 && (
          <div className={`mt-6 p-4 border-2 rounded-lg ${getRiskColor(riskLevel)}`}>
            <h3 className="font-bold mb-3">
              ⚠️ 위험도: <span className="uppercase">{riskLevel}</span>
            </h3>
            
            {/* 위험 신호 리스트 */}
            <div className="mb-4">
              <div className="font-semibold mb-2">감지된 신호:</div>
              {store.session.detectedSignals.map((sig, idx) => (
                <div key={idx} className="text-sm mb-1">
                  {sig.severity === 'high' ? '🔴' : '🟡'} {sig.signal}
                </div>
              ))}
            </div>

            {/* 조치 사항 미리 보기 */}
            {showActionPlan && (
              <div className="mt-4 p-3 bg-white bg-opacity-60 rounded">
                <div className="font-semibold mb-2">권장 조치:</div>
                {riskActions.map((action, idx) => (
                  <div key={idx} className="text-sm mb-1">
                    {action}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 조치 계획 */}
        {showActionPlan && (
          <div className="mt-6 p-4 border-2 border-purple-300 bg-purple-50 rounded-lg">
            <h3 className="font-bold text-purple-900 mb-3">✅ 권장 조치</h3>
            {riskActions.map((action, idx) => (
              <div key={idx} className="text-purple-800 mb-2">
                {action}
              </div>
            ))}
          </div>
        )}

        {/* 위험 신호 카드 - 기본 표시 */}
        {!showBriefing && store.session?.detectedSignals && store.session.detectedSignals.length > 0 && (
          <RiskSignalCard signals={store.session.detectedSignals} />
        )}

        {/* 선택지 표시 */}
        {lastMessage?.choices && lastMessage.choices.length > 0 && (
          <div className="mt-6">
            <QuickReply
              choices={lastMessage.choices}
              onChoose={handleChoiceSelect}
              isLoading={store.isLoading}
            />
          </div>
        )}

        {/* 입력창 */}
        {currentStep !== 'completed' && (
          <div className="mt-6">
            <ChatInput
              onSend={handleTextInput}
              placeholder="전화/문자/요구 내용 등을 간단히 적어주세요."
              disabled={store.isLoading}
            />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 행동 개입 화면 */}
      {store.showActionIntervention && (
        <ActionIntervention
          type={store.interventionType as any}
          onStopAction={() => {
            store.hideIntervention();
          }}
        />
      )}
    </div>
  );
};
