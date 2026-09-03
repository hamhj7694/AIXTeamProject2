import { useEffect, useRef } from 'react';
import { subscribeCaseChanged } from '../../services/caseSync';

export const useCaseSyncRefresh = (caseId: string | null, refresh: () => void | Promise<void>) => {
  const refreshRef = useRef(refresh);
  useEffect(() => { refreshRef.current = refresh; }, [refresh]);
  useEffect(() => subscribeCaseChanged(caseId, () => {
    void Promise.resolve(refreshRef.current()).catch(() => undefined);
  }), [caseId]);
};
