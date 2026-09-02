import { useEffect, useRef } from 'react';
import { conversationApi, type CaseDeltaEvent } from '../../services/conversationApi';

interface UseCaseEventRefreshOptions {
  caseId: string;
  cursor: string | null;
  onEvents: (events: CaseDeltaEvent[]) => void;
  intervalMs?: number;
}

/**
 * SSE endpoint is not available yet. Until it is provided, poll the public
 * append-only Case Event endpoint and let each screen refresh its Bundle.
 */
export const useCaseEventRefresh = ({
  caseId,
  cursor,
  onEvents,
  intervalMs = 2000,
}: UseCaseEventRefreshOptions) => {
  const cursorRef = useRef<string | null>(cursor);
  const onEventsRef = useRef(onEvents);

  useEffect(() => {
    cursorRef.current = cursor;
  }, [cursor]);

  useEffect(() => {
    onEventsRef.current = onEvents;
  }, [onEvents]);

  useEffect(() => {
    let active = true;
    let requesting = false;

    const poll = async () => {
      if (!active || requesting || !cursorRef.current) return;
      requesting = true;
      try {
        const events = await conversationApi.listEvents(caseId, Number(cursorRef.current));
        if (!active || events.length === 0) return;
        cursorRef.current = String(events[events.length - 1].event_id);
        onEventsRef.current(events);
      } catch {
        // The owning screen retains its existing error state and retries next cycle.
      } finally {
        requesting = false;
      }
    };

    const timer = window.setInterval(poll, intervalMs);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [caseId, intervalMs]);
};
