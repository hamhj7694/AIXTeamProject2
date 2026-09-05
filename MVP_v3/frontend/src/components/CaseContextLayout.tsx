import React, { useLayoutEffect, useRef, useState } from 'react';

const STORAGE_KEY = 'csr.bank.context-width.v1';
const DEFAULT_WIDTH = 400;
const MIN_WIDTH = 320;
const CHAT_MIN_WIDTH = 480;
const HANDLE_WIDTH = 8;

/** Layout-only preference: never changes Shared Case data or triggers AI. */
export const CaseContextLayout: React.FC<{ children: React.ReactNode; contextOpen: boolean }> = ({ children, contextOpen }) => {
  const container = useRef<HTMLDivElement>(null);
  const [preferred, setPreferred] = useState(() => {
    try {
      const stored = Number(localStorage.getItem(STORAGE_KEY));
      return Number.isFinite(stored) && stored >= MIN_WIDTH ? Math.min(stored, 800) : DEFAULT_WIDTH;
    } catch { return DEFAULT_WIDTH; }
  });
  const [maximum, setMaximum] = useState(DEFAULT_WIDTH);
  const width = Math.min(preferred, maximum);
  useLayoutEffect(() => {
    const element = container.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setMaximum(Math.max(MIN_WIDTH, Math.min(800, entry.contentRect.width - CHAT_MIN_WIDTH - HANDLE_WIDTH)));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const updateWidth = (value: number) => {
    const next = Math.round(Math.min(maximum, Math.max(MIN_WIDTH, value)));
    setPreferred(next);
    try { localStorage.setItem(STORAGE_KEY, String(next)); } catch { /* Private mode: retain session preference. */ }
  };
  const parts = React.Children.toArray(children);
  return <div ref={container} className={`case-room-grid ${contextOpen ? '' : 'is-context-closed'}`} style={{ '--context-width': `${width}px` } as React.CSSProperties}>
    {parts[0]}
    <div className="context-resize-handle" role="separator" tabIndex={0}
      aria-label="사건 맥락 너비 조절" aria-orientation="vertical"
      aria-valuemin={MIN_WIDTH} aria-valuemax={maximum} aria-valuenow={width}
      aria-valuetext={`${width}픽셀`} title="드래그 또는 좌우 방향키로 조절 · 두 번 클릭하면 기본 너비"
      onDoubleClick={() => updateWidth(DEFAULT_WIDTH)}
      onKeyDown={(event) => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End', 'Enter'].includes(event.key)) return;
        event.preventDefault();
        updateWidth(event.key === 'Home' ? MIN_WIDTH : event.key === 'End' ? maximum : event.key === 'Enter' ? DEFAULT_WIDTH : width + (event.key === 'ArrowLeft' ? 20 : -20));
      }}
      onPointerDown={(event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={(event) => {
        if (!event.currentTarget.hasPointerCapture(event.pointerId) || !container.current) return;
        updateWidth(container.current.getBoundingClientRect().right - event.clientX);
      }}
      onPointerUp={(event) => {
        if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
      }}
      onPointerCancel={(event) => {
        if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
      }}
    />
    {parts[1]}
  </div>;
};
