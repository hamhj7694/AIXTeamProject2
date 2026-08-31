import { create } from 'zustand';
import { ConsultationSession, Message } from '../../../types';
import { generateId, getCurrentTimestamp } from '../../../utils/helpers';
import { BANK_IMPERSONATION_FLOW } from '../../../data/mock/consultationMock';

interface ConsultationStore {
  session: ConsultationSession | null;
  messages: Message[];
  isLoading: boolean;
  showActionIntervention: boolean;
  interventionType?: 'stop_money_transfer' | 'stop_personal_info' | 'already_damaged';

  // 액션
  initializeSession: () => void;
  addMessage: (message: Message) => void;
  addUserMessage: (content: string) => void;
  updateCurrentStep: (step: any) => void;
  addRiskSignal: (signal: any) => void;
  addSituationInfo: (info: any) => void;
  showIntervention: (type: 'stop_money_transfer' | 'stop_personal_info' | 'already_damaged') => void;
  hideIntervention: () => void;
  completeConsultation: () => void;
  setLoading: (loading: boolean) => void;
}

export const useConsultationStore = create<ConsultationStore>((set, get) => ({
  session: null,
  messages: [],
  isLoading: false,
  showActionIntervention: false,
  interventionType: undefined,

  initializeSession: () => {
    const newSession: ConsultationSession = {
      id: generateId(),
      status: 'in_progress',
      currentStep: 'situation_check',
      userState: 'S0',
      riskLevel: 'low',
      messages: [],
      detectedSignals: [],
      situationInfo: [],
      actionPlan: [],
      completedActions: [],
      startedAt: getCurrentTimestamp(),
    };

    set({
      session: newSession,
      messages: [],
    });

    // 초기 메시지 추가
    const initialMessages: Message[] = [
      {
        id: generateId(),
        role: 'assistant',
        type: 'text',
        content: '안녕하세요. 함께 천천히 정리해볼게요.\n지금 당장 결론을 내리기보다, 상황을 하나씩 살펴보면 더 안전하게 판단할 수 있어요.\n편하게 말씀해 주세요.',
        createdAt: getCurrentTimestamp(),
      },
      {
        id: generateId(),
        role: 'assistant',
        type: 'question',
        content: '지금 어떤 상황인가요?',
        choices: [
          { id: 'call', label: '전화가 왔어요', value: 'call_received' },
          { id: 'message', label: '문자를 받았어요', value: 'message_received' },
          { id: 'money', label: '송금을 요구받았어요', value: 'money_requested' },
          { id: 'info', label: '개인정보를 요구받았어요', value: 'info_requested' },
          { id: 'app', label: '앱을 설치했어요', value: 'app_installed' },
          { id: 'unsure', label: '잘 모르겠어요', value: 'not_sure' },
        ],
        createdAt: getCurrentTimestamp(),
      },
    ];

    set({ messages: initialMessages });
  },

  addMessage: (message: Message) => {
    set((state) => ({
      messages: [...state.messages, message],
    }));
  },

  addUserMessage: (content: string) => {
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      type: 'text',
      content,
      createdAt: getCurrentTimestamp(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
    }));
  },

  updateCurrentStep: (step: any) => {
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          currentStep: step,
        },
      };
    });
  },

  addRiskSignal: (signal: any) => {
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          detectedSignals: [...state.session.detectedSignals, signal],
        },
      };
    });
  },

  addSituationInfo: (info: any) => {
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          situationInfo: [...state.session.situationInfo, info],
        },
      };
    });
  },

  showIntervention: (type: 'stop_money_transfer' | 'stop_personal_info' | 'already_damaged') => {
    set({
      showActionIntervention: true,
      interventionType: type,
    });
  },

  hideIntervention: () => {
    set({
      showActionIntervention: false,
      interventionType: undefined,
    });
  },

  completeConsultation: () => {
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          status: 'completed',
          currentStep: 'result',
          completedAt: getCurrentTimestamp(),
        },
      };
    });
  },

  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },
}));
