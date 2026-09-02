import { useConsultationStore } from '../store/consultationStore';

/**
 * 상담 기능 커스텀 훅
 */
export const useConsultation = () => {
  return useConsultationStore();
};
