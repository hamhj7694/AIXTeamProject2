import { useCallback, useEffect, useRef, useState } from 'react';

export function useScrollToLatest(latestKey: string, threshold = 80) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);
  const followLatest = useRef(true);
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    if (!initialized.current || followLatest.current) node.scrollTop = node.scrollHeight;
    initialized.current = true;
  }, [latestKey]);

  const onScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const node = event.currentTarget;
    const atLatest = node.scrollHeight - node.scrollTop - node.clientHeight < threshold;
    followLatest.current = atLatest;
    setShowJumpToLatest(!atLatest);
  }, [threshold]);

  const jumpToLatest = useCallback(() => {
    const node = scrollRef.current;
    if (!node) return;
    followLatest.current = true;
    node.scrollTo({ top: node.scrollHeight, behavior: 'smooth' });
    setShowJumpToLatest(false);
  }, []);

  return { scrollRef, showJumpToLatest, onScroll, jumpToLatest };
}
